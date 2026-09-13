from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,time,timezone
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
BASE_URL='https://apigw.trendyol.com'
@dataclass(frozen=True)
class TrendyolCredentials:
 seller_id:int; api_key:str; api_secret:str; user_agent:str
class TrendyolApiError(RuntimeError):pass
def _to_ms(value:date,end_of_day=False):return int(datetime.combine(value,time.max if end_of_day else time.min).replace(tzinfo=timezone.utc).timestamp()*1000)
def _request(creds,path,params):
 try:r=requests.get(f'{BASE_URL}{path}',params=params,headers={'User-Agent':creds.user_agent,'Accept':'application/json'},auth=HTTPBasicAuth(creds.api_key,creds.api_secret),timeout=45)
 except requests.RequestException as exc:raise TrendyolApiError(f'Trendyol API bağlantısı kurulamadı: {exc}') from exc
 if r.status_code==401:raise TrendyolApiError('Trendyol API yetkilendirmesi başarısız (401).')
 if r.status_code==429:raise TrendyolApiError('Trendyol API istek limiti aşıldı (429).')
 if not r.ok:raise TrendyolApiError(f'Trendyol API hata verdi ({r.status_code}): {r.text[:800]}')
 return r.json()
def _paged_content(creds,path,params,*,size=1000,source_type=None):
 page=0;rows=[]
 while True:
  p=dict(params);p.update({'page':page,'size':size});data=_request(creds,path,p);content=data.get('content') or []
  for raw in content:
   item=dict(raw)
   if source_type:item['_sourceTransactionType']=source_type
   rows.append(item)
  tp=data.get('totalPages')
  if (tp is not None and page+1>=int(tp)) or (tp is None and len(content)<size):break
  page+=1
  if page>2000:raise TrendyolApiError('Beklenmeyen sayfalama döngüsü durduruldu.')
 return rows

def fetch_payment_orders(creds,pages=3):
 rows=[];path=f'/integration/finance/che/sellers/{creds.seller_id}/payment-order'
 for page in range(max(1,pages)):
  data=_request(creds,path,{'page':page,'size':10});content=data.get('content') or [];rows.extend(content)
  tp=int(data.get('totalPages') or 0)
  if not content or (tp and page+1>=tp):break
 return pd.DataFrame(rows)

SETTLEMENT_TYPES=('Sale','Return','Discount','DiscountCancel','Coupon','CouponCancel','ProvisionPositive','ProvisionNegative','TYDiscount','TYDiscountCancel','TYCoupon','TYCouponCancel','ManuelRefund','ManuelRefundCancel','SellerRevenuePositive','SellerRevenueNegative','CommissionPositive','CommissionNegative','SellerRevenuePositiveCancel','SellerRevenueNegativeCancel','CommissionPositiveCancel','CommissionNegativeCancel')
def fetch_settlements_by_payment_order(creds,payment_order_id,transaction_types=SETTLEMENT_TYPES):
 rows=[];path=f'/integration/finance/che/sellers/{creds.seller_id}/settlements'
 for typ in transaction_types:
  try:rows.extend(_paged_content(creds,path,{'paymentOrderId':int(payment_order_id),'transactionType':typ},size=1000,source_type=typ))
  except TrendyolApiError as exc:
   if typ in {'Sale','Return'} or ('401' in str(exc) or '429' in str(exc)):raise
 return pd.DataFrame(rows)

# Domestic CHE docs expose PaymentOrder, DeductionInvoices, CreditNote and CommissionInvoice.
# PaymentOrder is deliberately excluded here: its amount is the payout being audited and
# adding it to expected current-account effects would double count the payment itself.
OTHER_FINANCIAL_TYPES=('DeductionInvoices','CreditNote','CommissionInvoice')
def fetch_other_financials_by_payment_order(creds,payment_order_id,transaction_types=OTHER_FINANCIAL_TYPES):
 rows=[];path=f'/integration/finance/che/sellers/{creds.seller_id}/otherfinancials'
 for typ in transaction_types:
  try:rows.extend(_paged_content(creds,path,{'paymentOrderId':int(payment_order_id),'transactionType':typ},size=1000,source_type=typ))
  except TrendyolApiError as exc:
   # Trendyol occasionally returns 500 for an optional type with no compatible records.
   # Never let that hide valid Sale/Return settlement reconciliation.
   if '401' in str(exc) or '429' in str(exc):raise
 return pd.DataFrame(rows)

def fetch_order_packages(creds,start_date,end_date,status=None):
 p={'startDate':_to_ms(start_date),'endDate':_to_ms(end_date,True),'orderByField':'PackageLastModifiedDate','orderByDirection':'ASC'}
 if status:p['status']=status
 return _paged_content(creds,f'/integration/order/sellers/{creds.seller_id}/v2/orders',p,size=200)
def packages_to_lines(packages):
 rows=[]
 for package in packages:
  order=str(package.get('orderNumber') or '');pid=package.get('shipmentPackageId') or package.get('id');status=package.get('status') or package.get('shipmentPackageStatus') or '';od=package.get('orderDate') or package.get('createdDate') or package.get('packageLastModifiedDate')
  for line in package.get('lines') or []:
   q=float(line.get('quantity') or 0);gross=float(line.get('lineGrossAmount') or line.get('price') or 0);unit=float(line.get('lineUnitPrice') or line.get('price') or 0);sd=float(line.get('lineSellerDiscount') or 0);td=float(line.get('lineTyDiscount') or 0);cr=float(line.get('commission') or line.get('commissionRate') or 0);vat=float(line.get('vatRate') or 0)
   rows.append({'Sipariş No':order,'Paket ID':pid,'Sipariş Tarihi':od,'Sipariş Statüsü':status,'Model Kodu':str(line.get('stockCode') or line.get('merchantSku') or '').strip(),'Barkod':str(line.get('barcode') or '').strip(),'Ürün Adı':str(line.get('productName') or '').strip(),'Ürün Adedi':q,'Birim Brüt Fiyat':gross,'Birim Net Fiyat':unit,'Teslim Ciro':unit*q,'Satıcı İndirimi':sd*q,'Trendyol İndirimi':td*q,'Komisyon Matrahı':gross*q,'Sipariş Komisyon Oranı %':cr,'Tahmini Komisyon':gross*q*cr/100,'KDV Oranı %':vat,'Line ID':line.get('lineId')})
 return pd.DataFrame(rows)
def fetch_settlements(creds,start_date,end_date,transaction_types=SETTLEMENT_TYPES):
 if (end_date-start_date).days>14:raise TrendyolApiError('Finans servisi tek sorguda en fazla 15 günlük tarih aralığı kabul ediyor.')
 rows=[];base={'startDate':_to_ms(start_date),'endDate':_to_ms(end_date,True)};path=f'/integration/finance/che/sellers/{creds.seller_id}/settlements'
 for typ in transaction_types:
  p=dict(base);p['transactionType']=typ
  try:rows.extend(_paged_content(creds,path,p,size=1000,source_type=typ))
  except TrendyolApiError as exc:
   if typ in {'Sale','Return'} or '400' not in str(exc):raise
 return pd.DataFrame(rows)
def fetch_other_financials(creds,start_date,end_date,transaction_type='DeductionInvoices',transaction_sub_type=None):
 p={'startDate':_to_ms(start_date),'endDate':_to_ms(end_date,True),'transactionType':transaction_type}
 if transaction_sub_type:p['transactionSubType']=transaction_sub_type
 return pd.DataFrame(_paged_content(creds,f'/integration/finance/che/sellers/{creds.seller_id}/otherfinancials',p,size=1000,source_type=transaction_type))
def fetch_cargo_invoice_items(creds,invoice_serial_number):
 serial=str(invoice_serial_number).strip()
 if not serial:return pd.DataFrame()
 out=pd.DataFrame(_paged_content(creds,f'/integration/finance/che/sellers/{creds.seller_id}/cargo-invoice/{serial}/items',{},size=500,source_type='CargoInvoiceItem'))
 if not out.empty:out['invoiceSerialNumber']=serial
 return out
def cargo_invoice_serials(deductions):
 if deductions is None or deductions.empty or 'id' not in deductions.columns:return []
 w=deductions.copy();text=pd.Series('',index=w.index,dtype='object')
 for c in ('transactionType','transactionSubType','description'):
  if c in w:text=text.str.cat(w[c].fillna('').astype(str),sep=' ')
 vals=w.loc[text.str.contains('kargo|cargo',case=False,regex=True,na=False),'id'].dropna().astype(str).str.strip();return [x for x in vals.drop_duplicates().tolist() if x]
def fetch_cargo_details_from_deductions(creds,deductions):
 frames=[];errors=[]
 for serial in cargo_invoice_serials(deductions):
  try:
   df=fetch_cargo_invoice_items(creds,serial)
   if not df.empty:frames.append(df)
  except TrendyolApiError as exc:errors.append({'invoiceSerialNumber':serial,'error':str(exc)})
 return (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()),pd.DataFrame(errors)
def cargo_summary(df):
 if df is None or df.empty:return {'outbound':0.,'return':0.,'other':0.,'total':0.,'rows':0}
 amount=pd.to_numeric(df.get('amount',0),errors='coerce').fillna(0).abs();typ=df.get('shipmentPackageType',pd.Series('',index=df.index)).fillna('').astype(str);ret=typ.str.contains('iade|return',case=False,regex=True,na=False);out=typ.str.contains('gönderi|gonderi|shipment|outbound',case=False,regex=True,na=False)&~ret;total=float(amount.sum());o=float(amount[out].sum());r=float(amount[ret].sum());return {'outbound':o,'return':r,'other':max(total-o-r,0),'total':total,'rows':len(df)}
def settlement_summary(df):
 if df is None or df.empty:return {'seller_revenue_net':0.,'commission_net':0.,'sales_revenue':0.,'return_revenue':0.,'sale_commission':0.,'return_commission':0.,'commission_credit':0.,'commission_debit':0.}
 w=df.copy();typ=w.get('_sourceTransactionType',pd.Series('',index=w.index)).astype(str);rev=pd.to_numeric(w.get('sellerRevenue',0),errors='coerce').fillna(0);comm=pd.to_numeric(w.get('commissionAmount',0),errors='coerce').fillna(0).abs();sale=float(comm[typ.eq('Sale')].sum());ret=float(comm[typ.eq('Return')].sum());return {'seller_revenue_net':float(rev[typ.eq('Sale')].abs().sum()-rev[typ.eq('Return')].abs().sum()),'commission_net':sale-ret,'sales_revenue':float(rev[typ.eq('Sale')].abs().sum()),'return_revenue':float(rev[typ.eq('Return')].abs().sum()),'sale_commission':sale,'return_commission':ret,'commission_credit':0.,'commission_debit':0.}
def other_financial_summary(df):
 if df is None or df.empty:return {'debt':0.,'credit':0.,'net_deduction':0.,'rows':0}
 debt=pd.to_numeric(df.get('debt',0),errors='coerce').fillna(0);credit=pd.to_numeric(df.get('credit',0),errors='coerce').fillna(0);return {'debt':float(debt.sum()),'credit':float(credit.sum()),'net_deduction':float((debt-credit).sum()),'rows':len(df)}