from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Iterable

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://apigw.trendyol.com"

@dataclass(frozen=True)
class TrendyolCredentials:
    seller_id: int
    api_key: str
    api_secret: str
    user_agent: str

class TrendyolApiError(RuntimeError):
    pass

def _to_ms(value: date, end_of_day: bool=False) -> int:
    t=time.max if end_of_day else time.min
    return int(datetime.combine(value,t).replace(tzinfo=timezone.utc).timestamp()*1000)

def _request(creds,path,params):
    try:
        r=requests.get(f"{BASE_URL}{path}",params=params,headers={"User-Agent":creds.user_agent,"Accept":"application/json"},auth=HTTPBasicAuth(creds.api_key,creds.api_secret),timeout=45)
    except requests.RequestException as exc:
        raise TrendyolApiError(f"Trendyol API bağlantısı kurulamadı: {exc}") from exc
    if r.status_code==401: raise TrendyolApiError("Trendyol API yetkilendirmesi başarısız (401).")
    if r.status_code==429: raise TrendyolApiError("Trendyol API istek limiti aşıldı (429).")
    if not r.ok: raise TrendyolApiError(f"Trendyol API hata verdi ({r.status_code}): {r.text[:800]}")
    try: return r.json()
    except ValueError as exc: raise TrendyolApiError("Trendyol API geçerli JSON döndürmedi.") from exc

def _paged_content(creds,path,params,*,size=1000,source_type=None):
    page=0; rows=[]
    while True:
        p=dict(params); p.update({"page":page,"size":size}); data=_request(creds,path,p); content=data.get("content") or []
        for raw in content:
            item=dict(raw)
            if source_type: item["_sourceTransactionType"]=source_type
            rows.append(item)
        tp=data.get("totalPages")
        if (tp is not None and page+1>=int(tp)) or (tp is None and len(content)<size): break
        page+=1
        if page>2000: raise TrendyolApiError("Beklenmeyen sayfalama döngüsü durduruldu.")
    return rows

def fetch_order_packages(creds,start_date,end_date,status=None):
    p={"startDate":_to_ms(start_date),"endDate":_to_ms(end_date,True),"orderByField":"PackageLastModifiedDate","orderByDirection":"ASC"}
    if status: p["status"]=status
    return _paged_content(creds,f"/integration/order/sellers/{creds.seller_id}/v2/orders",p,size=200)

def packages_to_lines(packages):
    rows=[]
    for package in packages:
        order=str(package.get("orderNumber") or "")
        pid=package.get("shipmentPackageId") or package.get("id")
        status=package.get("status") or package.get("shipmentPackageStatus") or ""
        od=package.get("orderDate") or package.get("createdDate") or package.get("packageLastModifiedDate")
        discount_names=", ".join(str(x.get("displayName") or "") for x in (package.get("discountDisplays") or []) if x.get("displayName"))
        for line in package.get("lines") or []:
            q=float(line.get("quantity") or 0)
            gross=float(line.get("lineGrossAmount") or line.get("price") or 0)
            unit=float(line.get("lineUnitPrice") or line.get("price") or 0)
            sd=float(line.get("lineSellerDiscount") or 0)
            td=float(line.get("lineTyDiscount") or 0)
            cr=float(line.get("commission") or line.get("commissionRate") or 0)
            vat=float(line.get("vatRate") or 0)
            commission_base_unit=max(gross-sd,0.0)
            commission_base=commission_base_unit*q
            rows.append({"Sipariş No":order,"Paket ID":pid,"Sipariş Tarihi":od,"Sipariş Statüsü":status,"Model Kodu":str(line.get("stockCode") or line.get("merchantSku") or "").strip(),"Barkod":str(line.get("barcode") or "").strip(),"Ürün Adı":str(line.get("productName") or "").strip(),"Ürün Adedi":q,"Birim Brüt Fiyat":gross,"Birim Net Fiyat":unit,"Teslim Ciro":unit*q,"Satıcı İndirimi":sd*q,"Trendyol İndirimi":td*q,"Komisyon Matrahı":commission_base,"Sipariş Komisyon Oranı %":cr,"Tahmini Komisyon":commission_base*cr/100,"KDV Oranı %":vat,"Line ID":line.get("lineId"),"Satış Kampanyası ID":line.get("salesCampaignId"),"İndirim Kampanyaları":discount_names})
    return pd.DataFrame(rows)

SETTLEMENT_TYPES=("Sale","Return","Discount","DiscountCancel","Coupon","CouponCancel","ProvisionPositive","ProvisionNegative","SellerRevenuePositive","SellerRevenueNegative","CommissionPositive","CommissionNegative","SellerRevenuePositiveCancel","SellerRevenueNegativeCancel","CommissionPositiveCancel","CommissionNegativeCancel")

def fetch_settlements(creds,start_date,end_date,transaction_types=SETTLEMENT_TYPES):
    if (end_date-start_date).days>14: raise TrendyolApiError("Finans servisi tek sorguda en fazla 15 günlük tarih aralığı kabul ediyor.")
    rows=[]; base={"startDate":_to_ms(start_date),"endDate":_to_ms(end_date,True)}; path=f"/integration/finance/che/sellers/{creds.seller_id}/settlements"
    for typ in transaction_types:
        p=dict(base); p["transactionType"]=typ
        try: rows.extend(_paged_content(creds,path,p,size=1000,source_type=typ))
        except TrendyolApiError as exc:
            if typ in {"Sale","Return"} or "400" not in str(exc): raise
    return pd.DataFrame(rows)

def fetch_other_financials(creds,start_date,end_date,transaction_type="DeductionInvoices",transaction_sub_type=None):
    p={"startDate":_to_ms(start_date),"endDate":_to_ms(end_date,True),"transactionType":transaction_type}
    if transaction_sub_type: p["transactionSubType"]=transaction_sub_type
    return pd.DataFrame(_paged_content(creds,f"/integration/finance/che/sellers/{creds.seller_id}/otherfinancials",p,size=1000,source_type=transaction_type))

def fetch_cargo_invoice_items(creds, invoice_serial_number):
    """Fetch item-level shipment/return cargo charges for one cargo invoice."""
    serial=str(invoice_serial_number).strip()
    if not serial:
        return pd.DataFrame()
    rows=_paged_content(creds,f"/integration/finance/che/sellers/{creds.seller_id}/cargo-invoice/{serial}/items",{},size=500,source_type="CargoInvoiceItem")
    out=pd.DataFrame(rows)
    if not out.empty:
        out["invoiceSerialNumber"]=serial
    return out

def cargo_invoice_serials(deductions):
    """Find cargo invoice serial numbers from DeductionInvoices rows.
    Trendyol documents the row id as the invoiceSerialNumber for cargo invoice rows.
    """
    if deductions is None or deductions.empty or "id" not in deductions.columns:
        return []
    w=deductions.copy()
    text=pd.Series("",index=w.index,dtype="object")
    for c in ("transactionType","transactionSubType","description"):
        if c in w.columns:
            text=text.str.cat(w[c].fillna("").astype(str),sep=" ")
    mask=text.str.contains("kargo|cargo",case=False,regex=True,na=False)
    vals=w.loc[mask,"id"].dropna().astype(str).str.strip()
    return [x for x in vals.drop_duplicates().tolist() if x]

def fetch_cargo_details_from_deductions(creds,deductions):
    """Resolve all cargo invoices in the deduction report to item-level cargo rows.
    One bad/old invoice should not block the rest; errors are returned separately.
    """
    frames=[]; errors=[]
    for serial in cargo_invoice_serials(deductions):
        try:
            df=fetch_cargo_invoice_items(creds,serial)
            if not df.empty: frames.append(df)
        except TrendyolApiError as exc:
            errors.append({"invoiceSerialNumber":serial,"error":str(exc)})
    details=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    return details,pd.DataFrame(errors)

def cargo_summary(df):
    if df is None or df.empty:
        return {"outbound":0.0,"return":0.0,"other":0.0,"total":0.0,"rows":0}
    w=df.copy()
    amount=pd.to_numeric(w["amount"] if "amount" in w else pd.Series(0.0,index=w.index),errors="coerce").fillna(0.0).abs()
    typ=w["shipmentPackageType"].fillna("").astype(str) if "shipmentPackageType" in w else pd.Series("",index=w.index)
    ret_mask=typ.str.contains("iade|return",case=False,regex=True,na=False)
    out_mask=typ.str.contains("gönderi|gonderi|shipment|outbound",case=False,regex=True,na=False) & ~ret_mask
    outbound=float(amount[out_mask].sum()); returned=float(amount[ret_mask].sum()); total=float(amount.sum())
    return {"outbound":outbound,"return":returned,"other":max(total-outbound-returned,0.0),"total":total,"rows":int(len(w))}

def settlement_summary(df):
    if df.empty: return {"seller_revenue_net":0.,"commission_net":0.,"sales_revenue":0.,"return_revenue":0.,"sale_commission":0.,"return_commission":0.,"commission_credit":0.,"commission_debit":0.}
    w=df.copy()
    for c in ("sellerRevenue","commissionAmount","debt","credit"):
        if c not in w: w[c]=0.
        w[c]=pd.to_numeric(w[c],errors="coerce").fillna(0.)
    s=w.get("_sourceTransactionType",pd.Series("",index=w.index)).astype(str)
    sale=float(w.loc[s.eq("Sale"),"commissionAmount"].abs().sum()); ret=float(w.loc[s.eq("Return"),"commissionAmount"].abs().sum())
    cneg=float(w.loc[s.eq("CommissionNegative"),"commissionAmount"].abs().sum()); cpos=float(w.loc[s.eq("CommissionPositive"),"commissionAmount"].abs().sum())
    cneg_cancel=float(w.loc[s.eq("CommissionNegativeCancel"),"commissionAmount"].abs().sum()); cpos_cancel=float(w.loc[s.eq("CommissionPositiveCancel"),"commissionAmount"].abs().sum())
    net_commission=sale-ret-cneg+cpos+cneg_cancel-cpos_cancel
    return {"seller_revenue_net":float(w.loc[s.eq("Sale"),"sellerRevenue"].abs().sum()-w.loc[s.eq("Return"),"sellerRevenue"].abs().sum()),"commission_net":net_commission,"sales_revenue":float(w.loc[s.eq("Sale"),"sellerRevenue"].abs().sum()),"return_revenue":float(w.loc[s.eq("Return"),"sellerRevenue"].abs().sum()),"sale_commission":sale,"return_commission":ret,"commission_credit":cneg-cneg_cancel,"commission_debit":cpos-cpos_cancel}

def _weighted_rate(group: pd.DataFrame, amount_col: str="commissionAmount") -> float:
    if "commissionRate" not in group.columns or group.empty: return 0.0
    rates=pd.to_numeric(group["commissionRate"],errors="coerce")
    amounts=pd.to_numeric(group.get(amount_col,0.),errors="coerce").abs().fillna(0.)
    mask=rates.notna() & (rates>0)
    if not mask.any(): return 0.0
    if amounts[mask].sum()>0: return float((rates[mask]*amounts[mask]).sum()/amounts[mask].sum())
    return float(rates[mask].mean())

def commission_reconciliation(lines,settlements):
    cols=["Sipariş No","Barkod","Sipariş Oranı %","Uygulanan Oran %","Komisyon Matrahı","Beklenen Komisyon","Satış Komisyonu","Komisyon Düzeltmesi","Gerçek Net Komisyon","Komisyon Avantajı","Fark TL","Durum"]
    if lines.empty or settlements.empty or "orderNumber" not in settlements.columns: return pd.DataFrame(columns=cols)
    l=lines.copy(); l["Sipariş No"]=l["Sipariş No"].astype(str).str.strip(); l["Barkod"]=l.get("Barkod","").astype(str).str.strip(); l["Tahmini Komisyon"]=pd.to_numeric(l["Tahmini Komisyon"],errors="coerce").fillna(0.); l["Komisyon Matrahı"]=pd.to_numeric(l.get("Komisyon Matrahı",0.),errors="coerce").fillna(0.); l["Sipariş Komisyon Oranı %"]=pd.to_numeric(l.get("Sipariş Komisyon Oranı %",0.),errors="coerce").fillna(0.)
    keys=["Sipariş No","Barkod"]
    order_ag=l.groupby(keys,as_index=False).agg({"Komisyon Matrahı":"sum","Tahmini Komisyon":"sum","Sipariş Komisyon Oranı %":"mean"}).rename(columns={"Tahmini Komisyon":"Beklenen Komisyon","Sipariş Komisyon Oranı %":"Sipariş Oranı %"})
    s=settlements.copy(); s["Sipariş No"]=s["orderNumber"].astype(str).str.strip(); s["Barkod"]=s.get("barcode","").astype(str).str.strip(); s["commissionAmount"]=pd.to_numeric(s.get("commissionAmount",0.),errors="coerce").fillna(0.); typ=s.get("_sourceTransactionType",pd.Series("",index=s.index)).astype(str)
    s["signed_commission"]=0.0
    sign_map={"Sale":1,"Return":-1,"CommissionPositive":1,"CommissionNegative":-1,"CommissionPositiveCancel":-1,"CommissionNegativeCancel":1}
    for t,sgn in sign_map.items(): s.loc[typ.eq(t),"signed_commission"]=s.loc[typ.eq(t),"commissionAmount"].abs()*sgn
    grouped=[]
    for (order,barcode),g in s.groupby(keys,dropna=False):
        gt=g.get("_sourceTransactionType",pd.Series("",index=g.index)).astype(str)
        sale=g.loc[gt.eq("Sale"),"commissionAmount"].abs().sum(); corr=g.loc[~gt.isin(["Sale","Return"]),"signed_commission"].sum(); net=g["signed_commission"].sum(); rate=_weighted_rate(g.loc[gt.eq("Sale")])
        grouped.append({"Sipariş No":order,"Barkod":barcode,"Satış Komisyonu":float(sale),"Komisyon Düzeltmesi":float(corr),"Gerçek Net Komisyon":float(net),"Uygulanan Oran %":rate})
    actual=pd.DataFrame(grouped)
    out=order_ag.merge(actual,on=keys,how="inner")
    if out.empty: return pd.DataFrame(columns=cols)
    out["Komisyon Avantajı"]=(out["Beklenen Komisyon"]-out["Gerçek Net Komisyon"]).clip(lower=0)
    out["Fark TL"]=out["Gerçek Net Komisyon"]-out["Beklenen Komisyon"]
    rate_drop=out["Sipariş Oranı %"]-out["Uygulanan Oran %"]
    tolerance=out["Beklenen Komisyon"].abs().clip(lower=1)*0.005
    out["Durum"]="🟢 Uyumlu"
    campaign=(rate_drop>0.10) & (out["Gerçek Net Komisyon"]<=out["Beklenen Komisyon"]+tolerance)
    correction=(out["Komisyon Düzeltmesi"]< -0.01) & (out["Gerçek Net Komisyon"]<=out["Beklenen Komisyon"]+tolerance)
    out.loc[campaign|correction,"Durum"]="💚 İndirimli Komisyon / Avantaj"
    over=out["Fark TL"]>tolerance
    out.loc[over,"Durum"]="🟠 Açıklanamayan Fark"
    unexplained=(~campaign)&(~correction)&(~over)&(out["Fark TL"].abs()>tolerance)
    out.loc[unexplained,"Durum"]="🟠 İncele"
    return out[cols].sort_values(["Durum","Komisyon Avantajı","Fark TL"],ascending=[True,False,False]).reset_index(drop=True)

def other_financial_summary(df):
    if df.empty:return {"debt":0.,"credit":0.,"net_deduction":0.}
    debt=pd.to_numeric(df["debt"] if "debt" in df else pd.Series(0.,index=df.index),errors="coerce").fillna(0.); credit=pd.to_numeric(df["credit"] if "credit" in df else pd.Series(0.,index=df.index),errors="coerce").fillna(0.)
    return {"debt":float(debt.sum()),"credit":float(credit.sum()),"net_deduction":float(debt.sum()-credit.sum())}

def test_connection(creds):
    today=datetime.now(timezone.utc).date()
    try: fetch_order_packages(creds,today,today); return True,"Trendyol API bağlantısı başarılı."
    except TrendyolApiError as exc:return False,str(exc)
