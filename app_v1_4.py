from __future__ import annotations
from datetime import datetime,timezone
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
import payout_auditor_v1_4 as pa
ty=importlib.reload(ty);pa=importlib.reload(pa)
TrendyolCredentials=ty.TrendyolCredentials
st.set_page_config(page_title='ProfitGO V1.4 - Hakediş Denetçisi',page_icon='◈',layout='wide')
st.markdown('''<style>[data-testid="stAppViewContainer"]{background:#f4f7fb}.block-container{max-width:1450px;padding-top:1.5rem}.pg{background:#fff;border:1px solid #e5eaf0;border-radius:18px;padding:22px;margin:14px 0}.hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:34px 38px;color:white}.hero h1{color:white}.hero em{color:#6ee7b7;font-style:normal}[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid #e5eaf0;border-radius:14px;padding:10px}</style>''',unsafe_allow_html=True)
def money(v):return f'{float(v):,.2f} TL'.replace(',','X').replace('.',',').replace('X','.')
def dt(ms):
 try:return datetime.fromtimestamp(float(ms)/1000,tz=timezone.utc).strftime('%d.%m.%Y')
 except:return '-'
try:
 seller_id=int(st.secrets['TRENDYOL_SELLER_ID']);creds=TrendyolCredentials(seller_id,str(st.secrets['TRENDYOL_API_KEY']),str(st.secrets['TRENDYOL_API_SECRET']),str(st.secrets.get('TRENDYOL_USER_AGENT',f'{seller_id} - ProfitGO')))
except Exception:st.error('Trendyol API bağlantısı yapılandırılmadı.');st.stop()
st.markdown('<div class="hero"><div>PROFITGO V1.4 • HAKEDİŞ DENETÇİSİ</div><h1>Trendyol <em>hakedişini doğru ödedi mi?</em></h1><p>Ödeme emrini paymentOrderId ile açar; o ödemeye giren satış, iade, indirim, komisyon düzeltmesi ve finansal kesintileri aynı ödeme kimliğinde mutabık eder.</p></div>',unsafe_allow_html=True)
if st.button('Son ödenmiş hakedişleri getir',type='primary',width='stretch'):
 try:
  with st.spinner('Trendyol ödeme emirleri alınıyor...'):st.session_state.v14_payment_orders=ty.fetch_payment_orders(creds,pages=3)
 except Exception as e:st.error(f'Ödeme emirleri alınamadı: {e}')
orders=st.session_state.get('v14_payment_orders',pd.DataFrame())
if orders is None or orders.empty:st.info('İlk adım: Son ödenmiş hakedişleri getir.');st.stop()
orders=orders.copy();orders['Etiket']=orders.apply(lambda r:f"{dt(r.get('payoutDate'))} • {money(r.get('amount',0))} • ID {r.get('id')}",axis=1)
choice=st.selectbox('Denetlenecek hakediş',orders['Etiket'].tolist(),index=0);po=orders.loc[orders['Etiket'].eq(choice)].iloc[0].to_dict()
if st.button('Bu hakedişi kuruşu kuruşuna denetle',type='primary',width='stretch'):
 try:
  with st.spinner('paymentOrderId içindeki tüm finans hareketleri mutabık ediliyor...'):
   s=ty.fetch_settlements_by_payment_order(creds,po['id']);o=ty.fetch_other_financials_by_payment_order(creds,po['id']);result=pa.audit(po,s,o);st.session_state.v14_payout_audit=result
 except Exception as e:st.error(f'Hakediş denetimi tamamlanamadı: {e}')
r=st.session_state.get('v14_payout_audit')
if not r or str(r.get('paymentOrderId'))!=str(po.get('id')):st.stop()
st.markdown('<div class="pg"><b>HAKEDİŞ MUTABAKATI</b><h3>Payment Order '+str(r['paymentOrderId'])+' • '+dt(r['payoutDate'])+'</h3></div>',unsafe_allow_html=True)
a,b,c,d=st.columns(4);a.metric('Hesaplanan Hakediş',money(r['expected']));b.metric("Trendyol'un Ödediği",money(r['paid']));c.metric('Fark',money(r['difference']));d.metric('Durum',r['status'])
if abs(r['difference'])<=0.05:st.success('Hakediş kuruş toleransı içinde mutabık. Trendyol ödeme emri ile ProfitGO hesabı eşleşiyor.')
else:st.warning(f"Bu hakedişte {money(abs(r['difference']))} mutabakat farkı var. Aşağıdaki hareketlerden kaynağını ayıracağız.")
e,f=st.columns(2);e.metric('Settlement Etkisi',money(r['settlement_effect']));f.metric('Diğer Finansal Etki',money(r['other_effect']))
with st.expander('Satış / iade / indirim / komisyon düzeltmeleri',expanded=abs(r['difference'])>0.05):
 sr=r['settlement_rows'];cols=[c for c in ['Tür','transactionDate','orderNumber','barcode','sellerRevenue','commissionAmount','debt','credit','Etki','description'] if c in sr.columns];st.dataframe(sr[cols] if cols else sr,width='stretch',hide_index=True)
with st.expander('Kesinti / fatura / diğer finans hareketleri',expanded=abs(r['difference'])>0.05):
 orows=r['other_rows'];cols=[c for c in ['Tür','transactionDate','transactionType','transactionSubType','description','debt','credit','Etki','id'] if c in orows.columns];st.dataframe(orows[cols] if cols else orows,width='stretch',hide_index=True)
st.caption('Ürün kârlılığı V1.4 içinde korunuyor ancak hakediş mutabakatı tamamlanana kadar ana ekrandan ikinci plana alındı.')
