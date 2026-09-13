from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
import commission_vat_reconciliation_v1_4 as cv

ty=importlib.reload(ty); cv=importlib.reload(cv)
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

st.markdown('<div class="hero"><div>PROFITGO V1.4 • VAT NORMALIZED COMMISSION ENGINE</div><h1>Komisyonu <em>aynı KDV bazında</em> karşılaştır.</h1><p>Order API beklenen komisyonu ile Finance API komisyonu KDV hariç aynı baza çevrilir. Komisyon KDV ayrıca gösterilir.</p></div>',unsafe_allow_html=True)
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
audit,vat_factor=cv.commission_reconciliation_vat(lines,settlements)
vat_rate=(vat_factor-1)*100
expected=float(audit["Beklenen Komisyon (KDV Hariç)"].sum()) if not audit.empty else 0
actual_net=float(audit["Gerçek Komisyon (KDV Hariç)"].sum()) if not audit.empty else 0
finance_gross=float(audit["Finance Komisyon (KDV Dahil)"].sum()) if not audit.empty else 0
commission_vat=float(audit["Komisyon KDV"].sum()) if not audit.empty else 0
adv=float(audit["Komisyon Avantajı"].sum()) if not audit.empty else 0
real_mask=audit["Durum"].eq("🟠 Gerçek Fark") if not audit.empty else pd.Series(dtype=bool)
real_diff=float(audit.loc[real_mask,"Fark TL"].clip(lower=0).sum()) if not audit.empty else 0
real_count=int(real_mask.sum()) if not audit.empty else 0

st.markdown('<div class="pg"><b>KDV NORMALİZASYONU</b><h3>8.340,82 TL yapay farkı KDV’den temizle</h3><p>Finance API komisyonu KDV dahil, Order API beklenen komisyonu KDV hariç aynı bazda karşılaştırılıyor.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4); k1.metric("Finance Komisyon • KDV Dahil",money(finance_gross)); k2.metric("Komisyon KDV",money(commission_vat),f"tespit %{vat_rate:.1f}"); k3.metric("Gerçek Komisyon • KDV Hariç",money(actual_net)); k4.metric("Beklenen • KDV Hariç",money(expected))
x1,x2,x3=st.columns(3); x1.metric("Komisyon Avantajı",money(adv)); x2.metric("KDV Sonrası Gerçek Fark",money(real_diff),f"{real_count} satır"); x3.metric("KDV Çarpanı",f"{vat_factor:.4f}")
if real_count==0:st.success("KDV normalizasyonundan sonra açıklanamayan pozitif komisyon farkı kalmadı.")
else:st.warning(f"KDV normalizasyonundan sonra {real_count} satırda toplam {money(real_diff)} gerçek fark adayı kaldı. Bunlar artık KDV kaynaklı değil; satır/lifecycle düzeyinde incelenecek.")

st.markdown('<div class="pg"><b>KESİNTİ HARİTASI</b><h3>Komisyon, kargo ve operasyonel kesintileri ayrı tut</h3></div>',unsafe_allow_html=True)
def cvv(name):
 z=dmap.loc[dmap["Kategori"].eq(name),"Tutar"] if not dmap.empty else pd.Series(dtype=float); return float(z.sum()) if not z.empty else 0
commission_invoice=cvv("Komisyon Faturası"); ad=cvv("Reklam / Pazarlama"); finance=cvv("Erken Ödeme / Finansman"); comp=cvv("Tazmin / Ürün Kaynaklı"); penalty=cvv("Ceza / İhlal"); unknown=cvv("Diğer / Tanımsız Fatura")
r1,r2,r3,r4=st.columns(4); r1.metric("Net Kesinti/Fatura",money(ded["net_deduction"])); r2.metric("Komisyon Faturası",money(commission_invoice)); r3.metric("Platform Hizmet Bedeli",money(pf["net_deduction"])); r4.metric("Toplam Kargo",money(cs["total"]))
r1,r2,r3,r4=st.columns(4); r1.metric("Reklam/Pazarlama",money(ad)); r2.metric("Erken Ödeme",money(finance)); r3.metric("Tazmin",money(comp)); r4.metric("Ceza/İhlal",money(penalty))
if not dmap.empty:st.dataframe(dmap,width="stretch",hide_index=True)

with st.expander("🔎 KDV normalize komisyon denetçisi",expanded=True):
 st.dataframe(audit,width="stretch",hide_index=True,column_config={c:st.column_config.NumberColumn(format="%.2f TL") for c in ["Komisyon Matrahı","Beklenen Komisyon (KDV Hariç)","Finance Komisyon (KDV Dahil)","Komisyon KDV","Gerçek Komisyon (KDV Hariç)","Komisyon Düzeltmesi (KDV Hariç)","Komisyon Avantajı","Fark TL"]})
with st.expander("🚚 Kargo detayları"):
 st.dataframe(cargo,width="stretch",hide_index=True) if not cargo.empty else st.info("Kargo detayı yok.")
with st.expander("🧾 Sınıflandırılmış kesintiler"):
 st.dataframe(drows,width="stretch",hide_index=True) if not drows.empty else st.info("Kesinti yok.")
with st.expander("Finans hareketleri"):
 st.dataframe(settlements,width="stretch",hide_index=True)
