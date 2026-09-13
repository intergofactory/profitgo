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

with st.sidebar:
 st.markdown("## ProfitGO")
 st.caption("V1.4 • API Finance Development")
 st.divider()
 st.write("**Komisyon + Kesinti Motoru**")
 st.caption("Order API + Finance API + Platform + Kargo")

st.markdown('''<div class="pg-hero"><div>PROFITGO V1.4 • FINANCE ENGINE</div><h1>Kesintiyi <em>kalem kalem</em> ayır.</h1><p>Komisyon, platform hizmet bedeli, gönderi kargo ve iade kargo birbirinden ayrılır. Açıklanamayan tutar ancak bu katmanlardan sonra anomali adayı olur.</p></div>''',unsafe_allow_html=True)

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

matched_expected=float(audit["Beklenen Komisyon"].sum()) if not audit.empty else 0.0
matched_actual=float(audit["Gerçek Net Komisyon"].sum()) if not audit.empty else 0.0
advantage=float(audit["Komisyon Avantajı"].sum()) if not audit.empty else 0.0
unexplained_mask=audit["Durum"].eq("🟠 Açıklanamayan Fark") if not audit.empty else pd.Series(dtype=bool)
unexplained=float(audit.loc[unexplained_mask,"Fark TL"].clip(lower=0).sum()) if not audit.empty else 0.0
campaign_count=int(audit["Durum"].eq("💚 İndirimli Komisyon / Avantaj").sum()) if not audit.empty else 0
unexplained_count=int(unexplained_mask.sum()) if not audit.empty else 0

platform_fee=pf["net_deduction"]
other_after_platform=ded["net_deduction"]-platform_fee
cargo_total=cargo["total"]
residual_after_known=ded["net_deduction"]-platform_fee-cargo_total

st.markdown('<div class="pg-card"><div class="pg-eyebrow">KESİNTİ HARİTASI</div><h3>Platform ve kargoyu ayrı hesapla</h3><p>Platform Hizmet Bedeli ile kargo faturaları komisyon değildir. ProfitGO bunları Net Kesinti/Fatura toplamından ayrı katmanlar halinde gösterir.</p></div>',unsafe_allow_html=True)

k1,k2,k3,k4=st.columns(4)
k1.metric("Net Kesinti/Fatura",money(ded["net_deduction"]))
k2.metric("Platform Hizmet Bedeli",money(platform_fee))
k3.metric("Toplam Kargo",money(cargo_total),f"{cargo['rows']} kalem")
k4.metric("Kalan Diğer Kesinti",money(residual_after_known))

c1,c2,c3,c4=st.columns(4)
c1.metric("Gönderi Kargo",money(cargo["outbound"]))
c2.metric("İade Kargo",money(cargo["return"]))
c3.metric("Sınıflanamayan Kargo",money(cargo["other"]))
c4.metric("Platform Payı",f"%{(platform_fee/ded['net_deduction']*100 if ded['net_deduction'] else 0):.2f}")

if platform_fee>0:
 st.success(f"Platform Hizmet Bedeli ayrı yakalandı: {money(platform_fee)}. Bu tutar komisyon farkının parçası değil.")
if cargo_total>0:
 st.success(f"Kargo faturaları ayrıştırıldı: Gönderi {money(cargo['outbound'])} • İade {money(cargo['return'])}.")
elif not cargo_errors.empty:
 st.warning("Kargo fatura detaylarında bazı kayıtlar çözülemedi; ham hata bilgisi aşağıdaki teknik bölümde tutuldu.")
else:
 st.info("Bu tarih aralığındaki DeductionInvoices kayıtlarında çözülebilir kargo faturası bulunmadı.")

st.markdown('<div class="pg-card"><div class="pg-eyebrow">KAMPANYA / TARİFE MOTORU</div><h3>İndirimli komisyonu anomali sanma</h3><p>Finance API komisyon oranı sipariş oranından düşükse veya CommissionNegative düzeltmesi varsa avantaj olarak ayrılır. Pozitif farklar ise henüz açıklanamayan fark olarak tutulur; fazla kesinti diye kesinleştirilmez.</p></div>',unsafe_allow_html=True)

k1,k2,k3,k4=st.columns(4)
k1.metric("Eşleşen Beklenen",money(matched_expected))
k2.metric("Eşleşen Gerçek",money(matched_actual))
k3.metric("Komisyon Avantajı",money(advantage),f"{campaign_count} satır")
k4.metric("Açıklanamayan Komisyon Farkı",money(unexplained),f"{unexplained_count} satır")

if campaign_count:
 st.success(f"{campaign_count} sipariş/ürün satırında indirimli komisyon veya komisyon iadesi/düzeltmesi sinyali bulundu. Toplam avantaj: {money(advantage)}")
if unexplained_count:
 st.warning(f"{unexplained_count} satırda henüz açıklanamayan komisyon farkı var: {money(unexplained)}. Platform ve kargo bu tutara eklenmiyor.")
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

with st.expander("🚚 Kargo fatura detayları",expanded=True):
 if cargo_details.empty:
  st.info("Kargo detay kaydı yok.")
 else:
  cols=[c for c in ["invoiceSerialNumber","shipmentPackageType","orderNumber","parcelUniqueId","amount","desi"] if c in cargo_details.columns]
  st.dataframe(cargo_details[cols],width="stretch",hide_index=True) if cols else st.dataframe(cargo_details,width="stretch",hide_index=True)

with st.expander("🧾 Platform hizmet bedeli kayıtları"):
 if platform_fees.empty:
  st.info("PlatformServiceFee filtresiyle kayıt dönmedi.")
 else:
  cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in platform_fees.columns]
  st.dataframe(platform_fees[cols],width="stretch",hide_index=True) if cols else st.dataframe(platform_fees,width="stretch",hide_index=True)

with st.expander("Finans hareketleri"):
 cols=[c for c in ["transactionDate","_sourceTransactionType","orderNumber","barcode","shipmentPackageId","sellerRevenue","commissionRate","commissionAmount","debt","credit"] if c in settlements.columns]
 st.dataframe(settlements[cols],width="stretch",hide_index=True) if cols else st.info("Finans hareketi yok.")

with st.expander("Tüm kesinti / fatura hareketleri"):
 cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in deductions.columns]
 st.dataframe(deductions[cols],width="stretch",hide_index=True) if cols else st.info("Kesinti hareketi yok.")

if not cargo_errors.empty:
 with st.expander("Teknik: çözülemeyen kargo faturaları"):
  st.dataframe(cargo_errors,width="stretch",hide_index=True)
