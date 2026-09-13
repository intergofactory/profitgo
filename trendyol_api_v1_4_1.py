from __future__ import annotations

import pandas as pd
from trendyol_api_v1_4 import *


def _finance_commission_vat_factor(settlements: pd.DataFrame) -> float:
    """Infer whether Finance API commissionAmount is VAT-inclusive.

    Trendyol's documented Sale example has commissionRate=12.5, sellerRevenue=382.4915
    and commissionAmount=67.4985. sellerRevenue + commissionAmount = 449.99;
    449.99 * 12.5% = 56.24875 and 56.24875 * 1.20 = 67.4985.
    We infer the factor from the seller's own Sale rows instead of hard-coding 20%.
    """
    if settlements is None or settlements.empty:
        return 1.0
    w=settlements.copy()
    typ=w.get("_sourceTransactionType",pd.Series("",index=w.index)).astype(str)
    w=w.loc[typ.eq("Sale")].copy()
    if w.empty:
        return 1.0
    amount=pd.to_numeric(w.get("commissionAmount",0.0),errors="coerce").abs()
    revenue=pd.to_numeric(w.get("sellerRevenue",0.0),errors="coerce").abs()
    rate=pd.to_numeric(w.get("commissionRate",0.0),errors="coerce")
    finance_base=revenue+amount
    expected_ex_vat=finance_base*rate/100.0
    valid=(amount>0)&(expected_ex_vat>0)&rate.between(0.01,50)
    if not valid.any():
        return 1.0
    ratios=(amount[valid]/expected_ex_vat[valid]).replace([float("inf"),float("-inf")],pd.NA).dropna()
    ratios=ratios[ratios.between(1.0,1.30)]
    if ratios.empty:
        return 1.0
    median=float(ratios.median())
    # Only normalize when the seller's own Finance rows clearly show VAT-inclusive commission.
    return median if 1.15 <= median <= 1.25 else 1.0


def commission_reconciliation(lines,settlements):
    cols=["Sipariş No","Barkod","Sipariş Oranı %","Uygulanan Oran %","Komisyon Matrahı","Beklenen Komisyon","Finance Komisyon (KDV Dahil)","Komisyon KDV","Gerçek Komisyon (KDV Hariç)","Komisyon Düzeltmesi (KDV Hariç)","Komisyon Avantajı","Fark TL","Durum"]
    if lines.empty or settlements.empty or "orderNumber" not in settlements.columns:
        return pd.DataFrame(columns=cols)

    vat_factor=_finance_commission_vat_factor(settlements)
    l=lines.copy()
    l["Sipariş No"]=l["Sipariş No"].astype(str).str.strip()
    l["Barkod"]=l.get("Barkod","").astype(str).str.strip()
    l["Tahmini Komisyon"]=pd.to_numeric(l["Tahmini Komisyon"],errors="coerce").fillna(0.)
    l["Komisyon Matrahı"]=pd.to_numeric(l.get("Komisyon Matrahı",0.),errors="coerce").fillna(0.)
    l["Sipariş Komisyon Oranı %"]=pd.to_numeric(l.get("Sipariş Komisyon Oranı %",0.),errors="coerce").fillna(0.)
    keys=["Sipariş No","Barkod"]
    order_ag=l.groupby(keys,as_index=False).agg({"Komisyon Matrahı":"sum","Tahmini Komisyon":"sum","Sipariş Komisyon Oranı %":"mean"}).rename(columns={"Tahmini Komisyon":"Beklenen Komisyon","Sipariş Komisyon Oranı %":"Sipariş Oranı %"})

    s=settlements.copy()
    s["Sipariş No"]=s["orderNumber"].astype(str).str.strip()
    s["Barkod"]=s.get("barcode","").astype(str).str.strip()
    s["commissionAmount"]=pd.to_numeric(s.get("commissionAmount",0.),errors="coerce").fillna(0.)
    typ=s.get("_sourceTransactionType",pd.Series("",index=s.index)).astype(str)
    s["commission_ex_vat"]=s["commissionAmount"].abs()/vat_factor
    s["signed_commission_ex_vat"]=0.0
    sign_map={"Sale":1,"Return":-1,"CommissionPositive":1,"CommissionNegative":-1,"CommissionPositiveCancel":-1,"CommissionNegativeCancel":1}
    for t,sgn in sign_map.items():
        s.loc[typ.eq(t),"signed_commission_ex_vat"]=s.loc[typ.eq(t),"commission_ex_vat"]*sgn

    grouped=[]
    for (order,barcode),g in s.groupby(keys,dropna=False):
        gt=g.get("_sourceTransactionType",pd.Series("",index=g.index)).astype(str)
        sale_gross=float(g.loc[gt.eq("Sale"),"commissionAmount"].abs().sum())
        sale_ex=float(g.loc[gt.eq("Sale"),"commission_ex_vat"].sum())
        corr_ex=float(g.loc[~gt.isin(["Sale","Return"]),"signed_commission_ex_vat"].sum())
        net_ex=float(g["signed_commission_ex_vat"].sum())
        rate=_weighted_rate(g.loc[gt.eq("Sale")])
        grouped.append({"Sipariş No":order,"Barkod":barcode,"Finance Komisyon (KDV Dahil)":sale_gross,"Komisyon KDV":sale_gross-sale_ex,"Gerçek Komisyon (KDV Hariç)":net_ex,"Komisyon Düzeltmesi (KDV Hariç)":corr_ex,"Uygulanan Oran %":rate})
    actual=pd.DataFrame(grouped)
    out=order_ag.merge(actual,on=keys,how="inner")
    if out.empty:
        return pd.DataFrame(columns=cols)

    out["Komisyon Avantajı"]=(out["Beklenen Komisyon"]-out["Gerçek Komisyon (KDV Hariç)" ]).clip(lower=0)
    out["Fark TL"]=out["Gerçek Komisyon (KDV Hariç)"]-out["Beklenen Komisyon"]
    rate_drop=out["Sipariş Oranı %"]-out["Uygulanan Oran %"]
    tolerance=out["Beklenen Komisyon"].abs().clip(lower=1)*0.005
    out["Durum"]="🟢 Uyumlu"
    campaign=(rate_drop>0.10)&(out["Gerçek Komisyon (KDV Hariç)"]<=out["Beklenen Komisyon"]+tolerance)
    correction=(out["Komisyon Düzeltmesi (KDV Hariç)"]< -0.01)&(out["Gerçek Komisyon (KDV Hariç)"]<=out["Beklenen Komisyon"]+tolerance)
    advantage=(out["Fark TL"] < -tolerance)
    out.loc[campaign|correction|advantage,"Durum"]="💚 İndirimli Komisyon / Avantaj"
    over=out["Fark TL"]>tolerance
    out.loc[over,"Durum"]="🟠 Açıklanamayan Fark"
    out.attrs["commission_vat_factor"]=vat_factor
    out.attrs["commission_vat_rate"]=(vat_factor-1.0)*100.0
    return out[cols].sort_values(["Durum","Komisyon Avantajı","Fark TL"],ascending=[True,False,False]).reset_index(drop=True)
