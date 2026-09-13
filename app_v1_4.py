from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
import commission_basis_v1_4 as cb

ty=importlib.reload(ty); cb=importlib.reload(cb)
TrendyolCredentials=ty.TrendyolCredentials
st.set_page_config(page_title="ProfitGO V1.4 - API Finans Merkezi",page_icon="◈",layout="wide")
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

st.markdown('<div class="hero"><div>PROFITGO V1.4 • COMMISSION BASIS ENGINE</div><h1>Komisyonu <em>doğru ticari matrahta</em> denetle.</h1><p>Satıcı indirimi finans hareketinde ayrıca oluşabildiği için komisyon matrahından ikinci kez düşülmez. Order API brüt ürün tutarı Finance API komisyonuyla sipariş+barkod bazında karşılaştırılır.</p></div>',unsafe_allow_html=True)
try:
 seller_id=int(st.secrets["TRENDYOL_SELLER_ID"]); creds=TrendyolCredentials(seller_id,str(st.secrets["TRENDYOL_API_KEY"]),str(st.secrets["TRENDYOL_API_SECRET"]),str(st.secrets.get("TRENDYOL_USER_AGENT",f"{seller_id} - ProfitGO")))
except Exception:
 st.error("Trendyol API bağlantısı yapılandırılmadı."); st.stop()
st.success(f"API aktif • Satıcı ID: {seller_id}")
a,b=st.columns(2)
with a:start_date=st.date_input("Başlangıç",date.today()-timedelta(days=13),max_value=date.today())
with b:end_date=st.date_input("Bitiş",date.today(),min_value=start_date,max_value=date.today())
if (end_date-start_date).days>14:st.warning("En fazla 15 günlük aralık seç.");st.stop()
if st.button("Trendyol'dan sipariş + finans verilerini çek",type="primary",width="stretch"):
 try:
  with st.spinner("Sipariş ve finans verileri alınıyor..."):
   packages=ty.fetch_order_packages(creds,start_date,end_date); lines=ty.packages_to_lines(packages); settlements=ty.fetch_settlements(creds,start_date,end_date); deductions=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices")
  try: platform=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices","PlatformServiceFee")
  except Exception: platform=pd.DataFrame()
  try:cargo,cargo_errors=ty.fetch_cargo_details_from_deductions(creds,deductions)
  except Exception as e:cargo=pd.DataFrame();cargo_errors=pd.DataFrame([{"error":str(e)}])
  st.session_state.update(v14_api_lines=lines,v14_finance_settlements=settlements,v14_finance_deductions=deductions,v14_platform_fees=platform,v14_cargo_details=cargo,v14_cargo_errors=cargo_errors)
  st.success(f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi".replace(",","."))
 except Exception as e:st.error(f"Entegrasyon hatası: {e}")
if "v14_api_lines" not in st.session_state:st.info("Verileri getir.");st.stop()
lines=st.session_state.v14_api_lines.copy(); settlements=st.session_state.v14_finance_settlements.copy(); deductions=st.session_state.v14_finance_deductions.copy(); platform=st.session_state.v14_platform_fees.copy(); cargo=st.session_state.v14_cargo_details.copy()
fin=ty.settlement_summary(settlements); ded=ty.other_financial_summary(deductions); pf=ty.other_financial_summary(platform); cs=ty.cargo_summary(cargo); dmap,drows=classify(deductions)
audit=cb.reconcile(lines,settlements); sm=cb.summary(audit)

st.markdown('<div class="pg"><b>KOMİSYON MATRAHI DÜZELTMESİ</b><h3>Satıcı indirimini komisyon matrahından ikinci kez düşme</h3><p>Önceki 8.340,82 TL alarmı KDV kaynaklı değildi. Canlı veride KDV hipotezi doğrulanmadı. Yeni motor komisyonu Order API brüt tutarı üzerinden hesaplayıp Finance API ile aynı sipariş+barkodda karşılaştırır.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4); k1.metric("Brüt Bazda Beklenen",money(sm['expected'])); k2.metric("Finance Gerçek Net",money(sm['actual'])); k3.metric("Pozitif Fark Adayı",money(sm['positive']),f"{sm['positive_rows']} satır"); k4.metric("Avantaj / Düzeltme",money(sm['negative']))
if sm['positive_rows']==0:st.success("Brüt komisyon matrahı düzeltmesinden sonra açıklanamayan pozitif komisyon farkı kalmadı.")
else:st.warning(f"Brüt matrah düzeltmesinden sonra {sm['positive_rows']} satırda {money(sm['positive'])} pozitif fark kaldı. Yalnızca bu bakiye lifecycle/paket düzeyinde incelenecek; 8.340,82 TL artık alarm tutarı değildir.")
st.caption(f"Eşleşen {sm['total_rows']} kayıt • Uyumlu {sm['ok_rows']} kayıt. Satıcı indirimleri Finance API'de ayrı Discount hareketleri olarak izlenir; komisyon matrahından tekrar düşülmez.")

st.markdown('<div class="pg"><b>KESİNTİ HARİTASI</b><h3>Komisyon, kargo ve operasyonel kesintileri ayrı tut</h3></div>',unsafe_allow_html=True)
def cvv(name):
 z=dmap.loc[dmap["Kategori"].eq(name),"Tutar"] if not dmap.empty else pd.Series(dtype=float); return float(z.sum()) if not z.empty else 0
commission_invoice=cvv("Komisyon Faturası"); ad=cvv("Reklam / Pazarlama"); finance=cvv("Erken Ödeme / Finansman"); comp=cvv("Tazmin / Ürün Kaynaklı"); penalty=cvv("Ceza / İhlal")
r1,r2,r3,r4=st.columns(4); r1.metric("Net Kesinti/Fatura",money(ded["net_deduction"])); r2.metric("Komisyon Faturası",money(commission_invoice)); r3.metric("Platform Hizmet Bedeli",money(pf["net_deduction"])); r4.metric("Toplam Kargo",money(cs["total"]))
r1,r2,r3,r4=st.columns(4); r1.metric("Reklam/Pazarlama",money(ad)); r2.metric("Erken Ödeme",money(finance)); r3.metric("Tazmin",money(comp)); r4.metric("Ceza/İhlal",money(penalty))
if not dmap.empty:st.dataframe(dmap,width="stretch",hide_index=True)

with st.expander("🔎 Brüt matrah komisyon denetçisi",expanded=True):
 st.dataframe(audit,width="stretch",hide_index=True,column_config={c:st.column_config.NumberColumn(format="%.2f TL") for c in ["Brüt Komisyon Matrahı","Satıcı İndirimi","Beklenen Komisyon","Gerçek Net Komisyon","Fark TL"]})
with st.expander("🚚 Kargo detayları"):
 if not cargo.empty:st.dataframe(cargo,width="stretch",hide_index=True)
 else:st.info("Kargo detayı yok.")
with st.expander("🧾 Sınıflandırılmış kesintiler"):
 if not drows.empty:st.dataframe(drows,width="stretch",hide_index=True)
 else:st.info("Kesinti yok.")
with st.expander("Finans hareketleri"):
 st.dataframe(settlements,width="stretch",hide_index=True)
