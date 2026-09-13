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
        order=str(package.get("orderNumber") or ""); pid=package.get("shipmentPackageId") or package.get("id"); status=package.get("status") or package.get("shipmentPackageStatus") or ""; od=package.get("orderDate") or package.get("createdDate") or package.get("packageLastModifiedDate")
        for line in package.get("lines") or []:
            q=float(line.get("quantity") or 0); gross=float(line.get("lineGrossAmount") or line.get("price") or 0); unit=float(line.get("lineUnitPrice") or line.get("price") or 0); sd=float(line.get("lineSellerDiscount") or 0); td=float(line.get("lineTyDiscount") or 0); cr=float(line.get("commission") or line.get("commissionRate") or 0); vat=float(line.get("vatRate") or 0)
            rows.append({"Sipariş No":order,"Paket ID":pid,"Sipariş Tarihi":od,"Sipariş Statüsü":status,"Model Kodu":str(line.get("stockCode") or line.get("merchantSku") or "").strip(),"Barkod":str(line.get("barcode") or "").strip(),"Ürün Adı":str(line.get("productName") or "").strip(),"Ürün Adedi":q,"Birim Brüt Fiyat":gross,"Birim Net Fiyat":unit,"Teslim Ciro":unit*q,"Satıcı İndirimi":sd*q,"Trendyol İndirimi":td*q,"Komisyon Oranı %":cr,"Tahmini Komisyon":unit*q*cr/100,"KDV Oranı %":vat,"Line ID":line.get("lineId")})
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

def settlement_summary(df):
    if df.empty: return {"seller_revenue_net":0.,"commission_net":0.,"sales_revenue":0.,"return_revenue":0.,"sale_commission":0.,"return_commission":0.}
    w=df.copy()
    for c in ("sellerRevenue","commissionAmount","debt","credit"):
        if c not in w: w[c]=0.
        w[c]=pd.to_numeric(w[c],errors="coerce").fillna(0.)
    s=w.get("_sourceTransactionType",pd.Series("",index=w.index)).astype(str)
    sale=float(w.loc[s.eq("Sale"),"commissionAmount"].abs().sum()); ret=float(w.loc[s.eq("Return"),"commissionAmount"].abs().sum())
    return {"seller_revenue_net":float(w.loc[s.eq("Sale"),"sellerRevenue"].abs().sum()-w.loc[s.eq("Return"),"sellerRevenue"].abs().sum()),"commission_net":sale-ret,"sales_revenue":float(w.loc[s.eq("Sale"),"sellerRevenue"].abs().sum()),"return_revenue":float(w.loc[s.eq("Return"),"sellerRevenue"].abs().sum()),"sale_commission":sale,"return_commission":ret}

def commission_reconciliation(lines,settlements):
    """Compare expected and actual commission only for order numbers present in BOTH APIs.
    This prevents accounting-date differences from becoming false alarms."""
    cols=["Sipariş No","Beklenen Komisyon","Gerçek Komisyon","Komisyon Farkı","Fark %","Durum"]
    if lines.empty or settlements.empty or "orderNumber" not in settlements.columns: return pd.DataFrame(columns=cols)
    l=lines.copy(); l["Sipariş No"]=l["Sipariş No"].astype(str).str.strip(); l["Tahmini Komisyon"]=pd.to_numeric(l["Tahmini Komisyon"],errors="coerce").fillna(0.)
    expected=l.groupby("Sipariş No",as_index=False)["Tahmini Komisyon"].sum().rename(columns={"Tahmini Komisyon":"Beklenen Komisyon"})
    s=settlements.copy(); s["Sipariş No"]=s["orderNumber"].astype(str).str.strip(); s["commissionAmount"]=pd.to_numeric(s.get("commissionAmount",0.),errors="coerce").fillna(0.); typ=s.get("_sourceTransactionType",pd.Series("",index=s.index)).astype(str)
    s["signed_commission"]=0.; s.loc[typ.eq("Sale"),"signed_commission"]=s.loc[typ.eq("Sale"),"commissionAmount"].abs(); s.loc[typ.eq("Return"),"signed_commission"]=-s.loc[typ.eq("Return"),"commissionAmount"].abs()
    actual=s.groupby("Sipariş No",as_index=False)["signed_commission"].sum().rename(columns={"signed_commission":"Gerçek Komisyon"})
    out=expected.merge(actual,on="Sipariş No",how="inner"); out=out[(out["Beklenen Komisyon"].abs()>0.01)|(out["Gerçek Komisyon"].abs()>0.01)].copy(); out["Komisyon Farkı"]=out["Gerçek Komisyon"]-out["Beklenen Komisyon"]; out["Fark %"]=out["Komisyon Farkı"]/out["Beklenen Komisyon"].replace(0,pd.NA)*100
    out["Durum"]="🟢 Uyumlu"; out.loc[out["Fark %"].abs()>=0.5,"Durum"]="🟠 İncele"; out.loc[out["Fark %"].abs()>=2,"Durum"]="🔴 Fark"
    return out.sort_values("Komisyon Farkı",key=lambda x:x.abs(),ascending=False)

def other_financial_summary(df):
    if df.empty:return {"debt":0.,"credit":0.,"net_deduction":0.}
    debt=pd.to_numeric(df["debt"] if "debt" in df else pd.Series(0.,index=df.index),errors="coerce").fillna(0.); credit=pd.to_numeric(df["credit"] if "credit" in df else pd.Series(0.,index=df.index),errors="coerce").fillna(0.)
    return {"debt":float(debt.sum()),"credit":float(credit.sum()),"net_deduction":float(debt.sum()-credit.sum())}

def test_connection(creds):
    today=datetime.now(timezone.utc).date()
    try: fetch_order_packages(creds,today,today); return True,"Trendyol API bağlantısı başarılı."
    except TrendyolApiError as exc:return False,str(exc)
