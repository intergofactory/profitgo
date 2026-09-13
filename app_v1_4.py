from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
import commission_basis_v1_4 as cb
import product_profitability_api_v1_4 as pp

ty=importlib.reload(ty); cb=importlib.reload(cb); pp=importlib.reload(pp)
TrendyolCredentials=ty.TrendyolCredentials
st.set_page_config(page_title="ProfitGO V1.4 - Gerçek Kârlılık",page_icon="◈",layout="wide")
st.markdown('''<style>[data-testid="stAppViewContainer"]{background:#f4f7fb}.block-container{max-width:1500px;padding-top:1.4rem}.pg{background:#fff;border:1px solid #e5eaf0;border-radius:18px;padding:20px;margin:14px 0}.hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:white}.hero h1{color:white}.hero em{color:#6ee7b7;font-style:normal}[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid #e5eaf0;border-radius:14px;padding:10px}</style>''',unsafe_allow_html=True)
def money(v): return f"{v:,.2f} TL".replace(",","X").replace(".",",").replace("X",".")
def classify(df):
 if df is None or df.empty:return pd.DataFrame(columns=["Kategori","Tutar","Kayıt"]),pd.DataFrame()
 w=df.copy(); debt=pd.to_numeric(w.get("debt",0),errors="coerce").fillna(0); credit=pd.to_numeric(w.get("credit",0),errors="coerce").fillna(0); w["Net Tutar"]=debt-credit
 text=pd.Series("",index=w.index,dtype="object")
 for c in ("transactionType","transactionSubType","description","invoiceType"):
  if c in w:text=text.str.cat(w[c].fillna("").astype(str),sep=" ")
 t=text.str.lower(); w["Kategori"]="Diğer / Tanımsız Fatura"
 rules=[("komisyon fatur","Komisyon Faturası"),("erken ödeme|erken odeme|early payment","Erken Ödeme / Finansman"),("kusurlu ürün|kusurlu urun|eksik ürün|eksik urun|tazmin","Tazmin / Ürün Kaynaklı"),("platformservice|platform hizmet","Platform Hizmet Bedeli"),("kargo|cargo","Kargo Faturası"),("ceza|penalty|ihlal","Ceza / İhlal"),("reklam|advert|sponsor|pazarlama|influencer","Reklam / Pazarlama")]
 for pat,name in rules:w.loc[t.str.contains(pat,case=False,regex=True,na=False),"Kategori"]=name
 s=w.groupby("Kategori",as_index=False).agg(Tutar=("Net Tutar","sum"),Kayıt=("Net Tutar","size")); return s.sort_values("Tutar",key=lambda x:x.abs(),ascending=False),w

def cat(dmap,name):
 z=dmap.loc[dmap['Kategori'].eq(name),'Tutar'] if not dmap.empty else pd.Series(dtype=float); return float(z.sum()) if not z.empty else 0.0

st.markdown('<div class="hero"><div>PROFITGO V1.4 • REAL PROFIT ENGINE</div><h1>SKU başına <em>gerçek net kârı</em> gör.</h1><p>Gerçek satış + Finance komisyonu + sipariş kargosu + platform/reklam/diğer gider payları + ürün maliyeti tek tabloda.</p></div>',unsafe_allow_html=True)
try:
 seller_id=int(st.secrets['TRENDYOL_SELLER_ID']); creds=TrendyolCredentials(seller_id,str(st.secrets['TRENDYOL_API_KEY']),str(st.secrets['TRENDYOL_API_SECRET']),str(st.secrets.get('TRENDYOL_USER_AGENT',f'{seller_id} - ProfitGO')))
except Exception: st.error('Trendyol API bağlantısı yapılandırılmadı.'); st.stop()
a,b=st.columns(2)
with a:start_date=st.date_input('Başlangıç',date.today()-timedelta(days=13),max_value=date.today())
with b:end_date=st.date_input('Bitiş',date.today(),min_value=start_date,max_value=date.today())
if (end_date-start_date).days>14:st.warning('En fazla 15 günlük aralık seç.');st.stop()
if st.button("Trendyol'dan sipariş + finans verilerini çek",type='primary',width='stretch'):
 try:
  with st.spinner('Gerçek finans verileri alınıyor...'):
   packages=ty.fetch_order_packages(creds,start_date,end_date); lines=ty.packages_to_lines(packages); settlements=ty.fetch_settlements(creds,start_date,end_date); deductions=ty.fetch_other_financials(creds,start_date,end_date,'DeductionInvoices')
   try:platform=ty.fetch_other_financials(creds,start_date,end_date,'DeductionInvoices','PlatformServiceFee')
   except Exception:platform=pd.DataFrame()
   try:cargo,cargo_errors=ty.fetch_cargo_details_from_deductions(creds,deductions)
   except Exception as e:cargo=pd.DataFrame();cargo_errors=pd.DataFrame([{'error':str(e)}])
   st.session_state.update(v14_api_lines=lines,v14_finance_settlements=settlements,v14_finance_deductions=deductions,v14_platform_fees=platform,v14_cargo_details=cargo)
   st.success(f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi".replace(',','.'))
 except Exception as e:st.error(f'Entegrasyon hatası: {e}')
if 'v14_api_lines' not in st.session_state:st.info('Verileri getir.');st.stop()
lines=st.session_state.v14_api_lines.copy(); settlements=st.session_state.v14_finance_settlements.copy(); deductions=st.session_state.v14_finance_deductions.copy(); platform=st.session_state.v14_platform_fees.copy(); cargo=st.session_state.v14_cargo_details.copy()
ded=ty.other_financial_summary(deductions); pf=ty.other_financial_summary(platform); cs=ty.cargo_summary(cargo); dmap,drows=classify(deductions); audit=cb.reconcile(lines,settlements); sm=cb.summary(audit)

st.markdown('<div class="pg"><b>KOMİSYON DENETÇİSİ • MUTABIK</b><h3>Brüt matrah kontrolü</h3></div>',unsafe_allow_html=True)
a1,a2,a3,a4=st.columns(4);a1.metric('Brüt Bazda Beklenen',money(sm['expected']));a2.metric('Finance Gerçek Net',money(sm['actual']));a3.metric('Pozitif Fark Adayı',money(sm['positive']));a4.metric('Avantaj / Düzeltme',money(sm['negative']))

models=lines[['Model Kodu','Barkod','Ürün Adı']].drop_duplicates().copy(); models['Birim Maliyet (KDV Dahil)']=0.0
reference_costs={'TKRCSHP01':370.0,'CT1.B':300.0}
for model,cost in reference_costs.items():models.loc[models['Model Kodu'].eq(model),'Birim Maliyet (KDV Dahil)']=cost
if 'v14_cost_master' in st.session_state:
 old=st.session_state.v14_cost_master
 if isinstance(old,pd.DataFrame) and not old.empty:
  saved=old[['Model Kodu','Birim Maliyet (KDV Dahil)']].drop_duplicates('Model Kodu').rename(columns={'Birim Maliyet (KDV Dahil)':'Kayitli Maliyet'})
  models=models.merge(saved,on='Model Kodu',how='left'); models['Birim Maliyet (KDV Dahil)']=pd.to_numeric(models['Kayitli Maliyet'],errors='coerce').combine_first(models['Birim Maliyet (KDV Dahil)']); models=models.drop(columns=['Kayitli Maliyet'])
st.markdown('<div class="pg"><b>MALİYET MERKEZİ</b><h3>SKU birim maliyetlerini gir</h3><p>CT1.B Beyaz Tekerlekli C Sehpa: 300 TL KDV dahil. Maliyetler oturum boyunca korunur ve SKU kârlılığına otomatik bağlanır.</p></div>',unsafe_allow_html=True)
edited=st.data_editor(models,width='stretch',hide_index=True,disabled=['Model Kodu','Barkod','Ürün Adı'],column_config={'Birim Maliyet (KDV Dahil)':st.column_config.NumberColumn(min_value=0.0,step=1.0,format='%.2f TL')},key='cost_editor')
st.session_state.v14_cost_master=edited.copy(); costs={str(r['Model Kodu']):float(r['Birim Maliyet (KDV Dahil)'] or 0) for _,r in edited.iterrows()}

ad=cat(dmap,'Reklam / Pazarlama'); finance=cat(dmap,'Erken Ödeme / Finansman'); comp=cat(dmap,'Tazmin / Ürün Kaynaklı'); penalty=cat(dmap,'Ceza / İhlal'); unknown=cat(dmap,'Diğer / Tanımsız Fatura'); shared=ad+finance+comp+penalty+unknown
profit=pp.build(lines,settlements,cargo,platform_total=pf['net_deduction'],shared_operational_total=shared,costs=costs); ps=pp.summary(profit)
st.markdown('<div class="pg"><b>GERÇEK ÜRÜN KÂRLILIĞI</b><h3>SKU bazında gerçekleşmiş sonuç</h3><p>Kargo siparişe doğrudan bağlanır. Komisyon Finance hareketinden gelir. Platform ve doğrudan SKU bağı olmayan operasyonel giderler satış geliri oranında dağıtılır. Komisyon faturası ikinci kez gider yazılmaz.</p></div>',unsafe_allow_html=True)
p1,p2,p3,p4=st.columns(4);p1.metric('Maliyeti Girilmiş SKU',ps['costed_skus']);p2.metric('Gerçek Net Kâr',money(ps['profit']));p3.metric('Net Kâr Marjı',f"%{ps['margin']:.2f}");p4.metric('Zarar Eden SKU',ps['loss_skus'])
if ps['missing_skus']:st.warning(f"{ps['missing_skus']} SKU için ürün maliyeti eksik. Toplam gerçek kâr yalnızca maliyeti girilmiş SKU'larda kesinleşir.")
else:st.success('Tüm SKU maliyetleri mevcut; ürün kârlılığı tam hesaplanıyor.')
cols=['Model Kodu','Barkod','Ürün Adı','Adet','Satış','Gerçek_Komisyon','Kargo','Platform Payı','Reklam/Diğer Payı','Birim Maliyet','Ürün Maliyeti','Gerçek Net Kâr','Net Marj %','Kârlılık']
st.dataframe(profit[[c for c in cols if c in profit]],width='stretch',hide_index=True,column_config={c:st.column_config.NumberColumn(format='%.2f TL') for c in ['Satış','Gerçek_Komisyon','Kargo','Platform Payı','Reklam/Diğer Payı','Birim Maliyet','Ürün Maliyeti','Gerçek Net Kâr']}|{'Net Marj %':st.column_config.NumberColumn(format='%.2f%%')})
with st.expander('Kesinti haritası'):st.dataframe(dmap,width='stretch',hide_index=True)
with st.expander('Brüt matrah komisyon denetçisi'):st.dataframe(audit,width='stretch',hide_index=True)
with st.expander('Kargo detayları'):
 if not cargo.empty:st.dataframe(cargo,width='stretch',hide_index=True)
 else:st.info('Kargo detayı yok.')
