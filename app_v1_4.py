from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty

ty=importlib.reload(ty)
TrendyolCredentials=ty.TrendyolCredentials

st.set_page_config(page_title="ProfitGO V1.4 - API Finans Merkezi",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown('''<style>:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0}[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}[data-testid="stSidebar"]{background:#0b1220}[data-testid="stSidebar"] *{color:#e2e8f0}.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em}.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}.pg-hero h1{color:#fff;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}</style>''',unsafe_allow_html=True)

def money(v):
 return f"{v:,.2f} TL".replace(",","X").replace(".",",").replace("X",".")

def classify_deductions(df):
 """Conservative classification of Trendyol DeductionInvoices.
 Exact invoice names are preferred. Unknown items stay unknown instead of being guessed.
 """
 if df is None or df.empty:
  return pd.DataFrame(columns=["Kategori","Tutar","Kayıt"]),pd.DataFrame()
 w=df.copy()
 debt=pd.to_numeric(w["debt"] if "debt" in w else pd.Series(0.0,index=w.index),errors="coerce").fillna(0.0)
 credit=pd.to_numeric(w["credit"] if "credit" in w else pd.Series(0.0,index=w.index),errors="coerce").fillna(0.0)
 w["Net Tutar"]=debt-credit
 text=pd.Series("",index=w.index,dtype="object")
 for col in ("transactionType","transactionSubType","description","invoiceType"):
  if col in w.columns:
   text=text.str.cat(w[col].fillna("").astype(str),sep=" ")
 t=text.str.lower()
 w["Kategori"]="Diğer / Tanımsız Fatura"

 # First classify explicit invoice types visible in the Finance API.
 w.loc[t.str.contains("komisyon fatur",regex=True,na=False),"Kategori"]="Komisyon Faturası"
 w.loc[t.str.contains("erken ödeme|erken odeme|early payment",regex=True,na=False),"Kategori"]="Erken Ödeme / Finansman"
 w.loc[t.str.contains("kusurlu ürün|kusurlu urun|eksik ürün|eksik urun|tazmin",regex=True,na=False),"Kategori"]="Tazmin / Ürün Kaynaklı"
 w.loc[t.str.contains("platformservice|platform hizmet",regex=True,na=False),"Kategori"]="Platform Hizmet Bedeli"
 w.loc[t.str.contains("kargo|cargo",regex=True,na=False),"Kategori"]="Kargo Faturası"
 w.loc[t.str.contains("ceza|penalty|ihlal",regex=True,na=False),"Kategori"]="Ceza / İhlal"
 w.loc[t.str.contains("reklam|advert|sponsor|pazarlama|influencer",regex=True,na=False),"Kategori"]="Reklam / Pazarlama"

 service_mask=t.str.contains("operasyon|operation|hizmet|service|servis|teknolojik|altyapı|altyapi",regex=True,na=False)
 w.loc[service_mask & w["Kategori"].eq("Diğer / Tanımsız Fatura"),"Kategori"]="Diğer Hizmet / Operasyon"

 summary=w.groupby("Kategori",as_index=False).agg(Tutar=("Net Tutar","sum"),Kayıt=("Net Tutar","size"))
 summary["Mutlak Tutar"]=summary["Tutar"].abs()
 summary=summary.sort_values("Mutlak Tutar",ascending=False).drop(columns="Mutlak Tutar")
 return summary,w

with st.sidebar:
 st.markdown("## ProfitGO")
 st.caption("V1.4 • API Finance Development")
 st.divider()
 st.write("**Komisyon + Kesinti Motoru**")
 st.caption("Order API + Finance API + Platform + Kargo + Kesinti Sınıfları")

st.markdown('''<div class="pg-hero"><div>PROFITGO V1.4 • FINANCE ENGINE</div><h1>Kesintiyi <em>kalem kalem</em> ayır.</h1><p>Komisyon faturası, platform hizmet bedeli, kargo, reklam, finansman ve tazmin kayıtları ayrı okunur. Aynı maliyetin iki kez sayılması engellenir.</p></div>''',unsafe_allow_html=True)

try:
 seller_id=int(st.secrets["TRENDYOL_SELLER_ID"])
 creds=TrendyolCredentials(seller_id,str(st.secrets["TRENDYOL_API_KEY"]),str(st.secrets["TRENDYOL_API_SECRET"]),str(st.secrets.get("TRENDYOL_USER_AGENT",f"{seller_id} - ProfitGO")))
except Exception:
 st.error("Trendyol API bağlantısı yapılandırılmadı.")
 st.stop()

st.success(f"API yapılandırması aktif • Satıcı ID: {seller_id}")
c1,c2=st.columns(2)
with c1:
 start_date=st.date_input("Başlangıç",value=date.today()-timedelta(days=13),max_value=date.today())
with c2:
 end_date=st.date_input("Bitiş",value=date.today(),min_value=start_date,max_value=date.today())
if (end_date-start_date).days>14:
 st.warning("15 gün veya daha kısa bir aralık seç.")
 st.stop()

if st.button("Trendyol'dan sipariş + finans verilerini çek",type="primary",width="stretch"):
 try:
  with st.spinner("Siparişler alınıyor..."):
   packages=ty.fetch_order_packages(creds,start_date,end_date)
   lines=ty.packages_to_lines(packages)
  with st.spinner("Cari hesap ve komisyon hareketleri alınıyor..."):
   settlements=ty.fetch_settlements(creds,start_date,end_date)
  with st.spinner("Kesinti/fatura hareketleri alınıyor..."):
   deductions=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices")
  with st.spinner("Platform hizmet bedelleri ayrıştırılıyor..."):
   try:
    platform_fees=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices","PlatformServiceFee")
   except Exception:
    platform_fees=pd.DataFrame()
  with st.spinner("Kargo faturaları sipariş seviyesine indiriliyor..."):
   try:
    cargo_details,cargo_errors=ty.fetch_cargo_details_from_deductions(creds,deductions)
   except Exception as exc:
    cargo_details=pd.DataFrame()
    cargo_errors=pd.DataFrame([{"error":str(exc)}])
  st.session_state.v14_api_lines=lines
  st.session_state.v14_finance_settlements=settlements
  st.session_state.v14_finance_deductions=deductions
  st.session_state.v14_platform_fees=platform_fees
  st.session_state.v14_cargo_details=cargo_details
  st.session_state.v14_cargo_errors=cargo_errors
  st.success(f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi • {len(deductions):,} kesinti hareketi • {len(cargo_details):,} kargo kalemi".replace(",","."))
 except Exception as exc:
  st.error(f"Entegrasyon hatası: {type(exc).__name__}: {exc}")

if "v14_api_lines" not in st.session_state:
 st.info("Tarih aralığını seç ve verileri getir.")
 st.stop()

lines=st.session_state.v14_api_lines.copy()
settlements=st.session_state.get("v14_finance_settlements",pd.DataFrame()).copy()
deductions=st.session_state.get("v14_finance_deductions",pd.DataFrame()).copy()
platform_fees=st.session_state.get("v14_platform_fees",pd.DataFrame()).copy()
cargo_details=st.session_state.get("v14_cargo_details",pd.DataFrame()).copy()
cargo_errors=st.session_state.get("v14_cargo_errors",pd.DataFrame()).copy()

if lines.empty:
 st.info("Sipariş bulunamadı.")
 st.stop()

revenue=float(pd.to_numeric(lines["Teslim Ciro"],errors="coerce").fillna(0).sum())
estimated=float(pd.to_numeric(lines["Tahmini Komisyon"],errors="coerce").fillna(0).sum())
seller_discount=float(pd.to_numeric(lines["Satıcı İndirimi"],errors="coerce").fillna(0).sum())
ty_discount=float(pd.to_numeric(lines["Trendyol İndirimi"],errors="coerce").fillna(0).sum())
fin=ty.settlement_summary(settlements)
ded=ty.other_financial_summary(deductions)
pf=ty.other_financial_summary(platform_fees)
cargo=ty.cargo_summary(cargo_details)
audit=ty.commission_reconciliation(lines,settlements)
deduction_map,deduction_rows=classify_deductions(deductions)

matched_expected=float(audit["Beklenen Komisyon"].sum()) if not audit.empty else 0.0
matched_actual=float(audit["Gerçek Net Komisyon"].sum()) if not audit.empty else 0.0
advantage=float(audit["Komisyon Avantajı"].sum()) if not audit.empty else 0.0
unexplained_mask=audit["Durum"].eq("🟠 Açıklanamayan Fark") if not audit.empty else pd.Series(dtype=bool)
unexplained=float(audit.loc[unexplained_mask,"Fark TL"].clip(lower=0).sum()) if not audit.empty else 0.0
campaign_count=int(audit["Durum"].eq("💚 İndirimli Komisyon / Avantaj").sum()) if not audit.empty else 0
unexplained_count=int(unexplained_mask.sum()) if not audit.empty else 0
platform_fee=pf["net_deduction"]
cargo_total=cargo["total"]

def category_value(name):
 if deduction_map.empty: return 0.0
 s=deduction_map.loc[deduction_map["Kategori"].eq(name),"Tutar"]
 return float(s.sum()) if not s.empty else 0.0

commission_invoice_total=category_value("Komisyon Faturası")
penalty_total=category_value("Ceza / İhlal")
ad_total=category_value("Reklam / Pazarlama")
finance_total=category_value("Erken Ödeme / Finansman")
compensation_total=category_value("Tazmin / Ürün Kaynaklı")
service_total=category_value("Diğer Hizmet / Operasyon")
unknown_total=category_value("Diğer / Tanımsız Fatura")

# DeductionInvoices contains commission invoices too. Since commission is already measured from settlements,
# do not add commission invoices again when calculating additional operational deductions.
extra_operational=ded["net_deduction"]-commission_invoice_total
residual_after_known=ded["net_deduction"]-commission_invoice_total-platform_fee-cargo_total-ad_total-finance_total-compensation_total-penalty_total-service_total

st.markdown('<div class="pg-card"><div class="pg-eyebrow">KESİNTİ HARİTASI</div><h3>Komisyon faturasını diğer kesintilerden ayır</h3><p>DeductionInvoices içinde komisyon faturası da bulunabilir. Komisyon zaten Finance settlements üzerinden ölçüldüğü için bu fatura ikinci kez maliyete eklenmez.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4)
k1.metric("Net Kesinti/Fatura",money(ded["net_deduction"]))
k2.metric("Komisyon Faturası",money(commission_invoice_total))
k3.metric("Ek Operasyonel Kesinti",money(extra_operational))
k4.metric("Tanımsız Kalan",money(unknown_total))

c1,c2,c3,c4=st.columns(4)
c1.metric("Platform Hizmet Bedeli",money(platform_fee))
c2.metric("Toplam Kargo",money(cargo_total),f"{cargo['rows']} kalem")
c3.metric("Gönderi Kargo",money(cargo["outbound"]))
c4.metric("İade Kargo",money(cargo["return"]))

if commission_invoice_total:
 st.success(f"Komisyon faturası ayrı yakalandı: {money(commission_invoice_total)}. Bu tutar, settlements komisyonuna eklenerek ikinci kez maliyet yazılmayacak.")
if platform_fee>0:
 st.success(f"Platform Hizmet Bedeli: {money(platform_fee)}. Komisyon farkının parçası değil.")
if cargo_total>0:
 st.success(f"Kargo faturaları: Gönderi {money(cargo['outbound'])} • İade {money(cargo['return'])}.")

st.markdown('<div class="pg-card"><div class="pg-eyebrow">DİĞER KESİNTİLER</div><h3>Operasyonel kesintileri gerçek türüne ayır</h3><p>Reklam, erken ödeme/finansman, tazmin, ceza ve hizmet faturaları ayrı gösterilir. Belirsiz kayıtlar Tanımsız kalır.</p></div>',unsafe_allow_html=True)
d1,d2,d3,d4=st.columns(4)
d1.metric("Reklam / Pazarlama",money(ad_total))
d2.metric("Erken Ödeme / Finansman",money(finance_total))
d3.metric("Tazmin / Ürün Kaynaklı",money(compensation_total))
d4.metric("Ceza / İhlal",money(penalty_total))
e1,e2,e3=st.columns(3)
e1.metric("Diğer Hizmet / Operasyon",money(service_total))
e2.metric("Tanımsız Fatura",money(unknown_total))
e3.metric("Kontrol Bakiyesi",money(residual_after_known))

if not deduction_map.empty:
 st.dataframe(deduction_map,width="stretch",hide_index=True,column_config={"Tutar":st.column_config.NumberColumn(format="%.2f TL"),"Kayıt":st.column_config.NumberColumn(format="%d")})
 if abs(float(deduction_map["Tutar"].sum())-ded["net_deduction"])<0.05:
  st.success("Kesinti sınıfları toplamı Net Kesinti/Fatura toplamıyla mutabık.")
 else:
  st.warning("Kesinti sınıfları ile Net Kesinti/Fatura arasında mutabakat farkı var; bu fark ayrıca incelenmeli.")

st.markdown('<div class="pg-card"><div class="pg-eyebrow">KAMPANYA / TARİFE MOTORU</div><h3>İndirimli komisyonu anomali sanma</h3><p>Finance API komisyon oranı sipariş oranından düşükse veya CommissionNegative düzeltmesi varsa avantaj olarak ayrılır. Pozitif farklar ise henüz açıklanamayan fark olarak tutulur; fazla kesinti diye kesinleştirilmez.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4)
k1.metric("Eşleşen Beklenen",money(matched_expected))
k2.metric("Eşleşen Gerçek",money(matched_actual))
k3.metric("Komisyon Avantajı",money(advantage),f"{campaign_count} satır")
k4.metric("Açıklanamayan Komisyon Farkı",money(unexplained),f"{unexplained_count} satır")
if campaign_count:
 st.success(f"{campaign_count} sipariş/ürün satırında indirimli komisyon veya komisyon iadesi/düzeltmesi sinyali bulundu. Toplam avantaj: {money(advantage)}")
if unexplained_count:
 st.warning(f"{unexplained_count} satırda henüz açıklanamayan komisyon farkı var: {money(unexplained)}. Platform, kargo ve komisyon faturası bu tutara eklenmiyor.")
elif not audit.empty:
 st.info("Eşleşen kayıtlarda açıklanamayan pozitif komisyon farkı görünmüyor.")

a,b,c,d=st.columns(4)
a.metric("Dönem Tahmini Komisyon",money(estimated))
b.metric("Satış Komisyonu",money(fin["sale_commission"]))
c.metric("Komisyon İade/Düzeltme Kredisi",money(fin["return_commission"]+fin.get("commission_credit",0)))
d.metric("Platform Hizmet Bedeli",money(platform_fee))
st.caption("Dönem toplamları bilgi amaçlıdır. Alarm motoru yalnızca Order ve Finance API'de aynı sipariş+barkod eşleşen kayıtları kullanır. Trendyol indirimi: "+money(ty_discount)+" • Satıcı indirimi: "+money(seller_discount))

with st.expander("💚 Komisyon kampanyası / tarife denetçisi",expanded=True):
 if audit.empty:
  st.info("Eşleşen kayıt yok.")
 else:
  st.dataframe(audit,width="stretch",hide_index=True,column_config={"Sipariş Oranı %":st.column_config.NumberColumn(format="%.2f%%"),"Uygulanan Oran %":st.column_config.NumberColumn(format="%.2f%%"),"Komisyon Matrahı":st.column_config.NumberColumn(format="%.2f TL"),"Beklenen Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Satış Komisyonu":st.column_config.NumberColumn(format="%.2f TL"),"Komisyon Düzeltmesi":st.column_config.NumberColumn(format="%.2f TL"),"Gerçek Net Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Komisyon Avantajı":st.column_config.NumberColumn(format="%.2f TL"),"Fark TL":st.column_config.NumberColumn(format="%.2f TL")})

with st.expander("🚚 Kargo fatura detayları"):
 if cargo_details.empty:
  st.info("Kargo detay kaydı yok.")
 else:
  cols=[c for c in ["invoiceSerialNumber","shipmentPackageType","orderNumber","parcelUniqueId","amount","desi"] if c in cargo_details.columns]
  st.dataframe(cargo_details[cols] if cols else cargo_details,width="stretch",hide_index=True)

with st.expander("🧾 Sınıflandırılmış kesinti/fatura kayıtları",expanded=True):
 if deduction_rows.empty:
  st.info("Kesinti kaydı yok.")
 else:
  cols=[c for c in ["Kategori","transactionDate","transactionType","transactionSubType","description","Net Tutar","debt","credit","id"] if c in deduction_rows.columns]
  st.dataframe(deduction_rows[cols] if cols else deduction_rows,width="stretch",hide_index=True,column_config={"Net Tutar":st.column_config.NumberColumn(format="%.2f TL")})

with st.expander("🧾 Platform hizmet bedeli kayıtları"):
 if platform_fees.empty:
  st.info("PlatformServiceFee filtresiyle kayıt dönmedi.")
 else:
  cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in platform_fees.columns]
  st.dataframe(platform_fees[cols] if cols else platform_fees,width="stretch",hide_index=True)

with st.expander("Finans hareketleri"):
 cols=[c for c in ["transactionDate","_sourceTransactionType","orderNumber","barcode","shipmentPackageId","sellerRevenue","commissionRate","commissionAmount","debt","credit"] if c in settlements.columns]
 if cols:
  st.dataframe(settlements[cols],width="stretch",hide_index=True)
 else:
  st.info("Finans hareketi yok.")

if not cargo_errors.empty:
 with st.expander("Teknik: çözülemeyen kargo faturaları"):
  st.dataframe(cargo_errors,width="stretch",hide_index=True)
