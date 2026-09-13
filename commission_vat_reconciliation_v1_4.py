from __future__ import annotations

import pandas as pd


def infer_commission_vat_factor(settlements: pd.DataFrame) -> float:
    """Infer the multiplier embedded in Finance commissionAmount from Sale rows.

    Trendyol Finance Sale rows expose sellerRevenue, commissionAmount and
    commissionRate. For clean rows, sellerRevenue + commissionAmount is the
    commission-bearing gross amount, so:
      factor = commissionAmount / ((sellerRevenue + commissionAmount) * rate)
    A median near 1.20 means Finance commissionAmount includes 20% VAT.
    """
    if settlements is None or settlements.empty:
        return 1.0
    w=settlements.copy()
    typ=w.get("_sourceTransactionType",pd.Series("",index=w.index)).astype(str)
    w=w.loc[typ.eq("Sale")].copy()
    if w.empty:
        return 1.0
    for c in ("sellerRevenue","commissionAmount","commissionRate"):
        w[c]=pd.to_numeric(w.get(c,0.0),errors="coerce").fillna(0.0)
    base=(w["sellerRevenue"].abs()+w["commissionAmount"].abs())
    expected=base*w["commissionRate"].abs()/100.0
    valid=(expected>0.01)&(w["commissionAmount"].abs()>0.01)
    ratios=(w.loc[valid,"commissionAmount"].abs()/expected[valid]).replace([float("inf"),-float("inf")],pd.NA).dropna()
    ratios=ratios[(ratios>=0.95)&(ratios<=1.30)]
    if ratios.empty:
        return 1.0
    factor=float(ratios.median())
    # Stabilize common VAT factors; otherwise keep the observed median.
    if abs(factor-1.20)<=0.035:
        return 1.20
    if abs(factor-1.10)<=0.025:
        return 1.10
    if abs(factor-1.00)<=0.02:
        return 1.00
    return factor


def commission_reconciliation_vat(lines: pd.DataFrame, settlements: pd.DataFrame) -> tuple[pd.DataFrame,float]:
    cols=["Sipariş No","Barkod","Sipariş Oranı %","Uygulanan Oran %","Komisyon Matrahı","Beklenen Komisyon (KDV Hariç)","Finance Komisyon (KDV Dahil)","Komisyon KDV","Gerçek Komisyon (KDV Hariç)","Komisyon Düzeltmesi (KDV Hariç)","Komisyon Avantajı","Fark TL","Durum"]
    if lines is None or lines.empty or settlements is None or settlements.empty or "orderNumber" not in settlements.columns:
        return pd.DataFrame(columns=cols),1.0

    factor=infer_commission_vat_factor(settlements)
    l=lines.copy()
    l["Sipariş No"]=l["Sipariş No"].astype(str).str.strip()
    l["Barkod"]=l.get("Barkod","").astype(str).str.strip()
    for c in ("Komisyon Matrahı","Tahmini Komisyon","Sipariş Komisyon Oranı %"):
        l[c]=pd.to_numeric(l.get(c,0.0),errors="coerce").fillna(0.0)
    keys=["Sipariş No","Barkod"]
    order_ag=l.groupby(keys,as_index=False).agg({"Komisyon Matrahı":"sum","Tahmini Komisyon":"sum","Sipariş Komisyon Oranı %":"mean"}).rename(columns={"Tahmini Komisyon":"Beklenen Komisyon (KDV Hariç)","Sipariş Komisyon Oranı %":"Sipariş Oranı %"})

    s=settlements.copy()
    s["Sipariş No"]=s["orderNumber"].astype(str).str.strip()
    s["Barkod"]=s.get("barcode","").astype(str).str.strip()
    s["commissionAmount"]=pd.to_numeric(s.get("commissionAmount",0.0),errors="coerce").fillna(0.0)
    s["commissionRate"]=pd.to_numeric(s.get("commissionRate",0.0),errors="coerce").fillna(0.0)
    typ=s.get("_sourceTransactionType",pd.Series("",index=s.index)).astype(str)
    sign_map={"Sale":1,"Return":-1,"CommissionPositive":1,"CommissionNegative":-1,"CommissionPositiveCancel":-1,"CommissionNegativeCancel":1}
    s["signed_gross_commission"]=0.0
    for t,sgn in sign_map.items():
        s.loc[typ.eq(t),"signed_gross_commission"]=s.loc[typ.eq(t),"commissionAmount"].abs()*sgn
    s["signed_net_commission"]=s["signed_gross_commission"]/factor

    grouped=[]
    for (order,barcode),g in s.groupby(keys,dropna=False):
        gt=g.get("_sourceTransactionType",pd.Series("",index=g.index)).astype(str)
        sale_gross=float(g.loc[gt.eq("Sale"),"commissionAmount"].abs().sum())
        sale_net=sale_gross/factor
        corr_net=float(g.loc[~gt.isin(["Sale","Return"]),"signed_net_commission"].sum())
        actual_net=float(g["signed_net_commission"].sum())
        vat=max(sale_gross-sale_net,0.0)
        sale_rows=g.loc[gt.eq("Sale")]
        rates=pd.to_numeric(sale_rows.get("commissionRate",0.0),errors="coerce").fillna(0.0)
        amounts=pd.to_numeric(sale_rows.get("commissionAmount",0.0),errors="coerce").abs().fillna(0.0)
        rate=float((rates*amounts).sum()/amounts.sum()) if amounts.sum()>0 else 0.0
        grouped.append({"Sipariş No":order,"Barkod":barcode,"Finance Komisyon (KDV Dahil)":sale_gross,"Komisyon KDV":vat,"Gerçek Komisyon (KDV Hariç)":actual_net,"Komisyon Düzeltmesi (KDV Hariç)":corr_net,"Uygulanan Oran %":rate})
    actual=pd.DataFrame(grouped)
    out=order_ag.merge(actual,on=keys,how="inner")
    if out.empty:
        return pd.DataFrame(columns=cols),factor

    expected=out["Beklenen Komisyon (KDV Hariç)"]
    actual_net=out["Gerçek Komisyon (KDV Hariç)"]
    out["Komisyon Avantajı"]=(expected-actual_net).clip(lower=0.0)
    out["Fark TL"]=actual_net-expected
    tolerance=expected.abs().clip(lower=1.0)*0.005
    rate_drop=out["Sipariş Oranı %"]-out["Uygulanan Oran %"]
    out["Durum"]="🟢 Uyumlu"
    campaign=(rate_drop>0.10)&(actual_net<=expected+tolerance)
    correction=(out["Komisyon Düzeltmesi (KDV Hariç)"]<-0.01)&(actual_net<=expected+tolerance)
    out.loc[campaign|correction,"Durum"]="💚 İndirimli Komisyon / Avantaj"
    over=out["Fark TL"]>tolerance
    out.loc[over,"Durum"]="🟠 Gerçek Fark"
    under=(~campaign)&(~correction)&(~over)&(out["Fark TL"]<-tolerance)
    out.loc[under,"Durum"]="🟡 Düşük Komisyon / İncele"
    return out[cols].sort_values(["Durum","Fark TL"],ascending=[True,False]).reset_index(drop=True),factor
