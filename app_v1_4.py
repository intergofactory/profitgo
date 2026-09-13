from __future__ import annotations
from datetime import date,timedelta
import importlib
import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty
ty=importlib.reload(ty); TrendyolCredentials=ty.TrendyolCredentials; TrendyolApiError=ty.TrendyolApiError
st.set_page_config(page_title="ProfitGO V1.4 - API Finans Merkezi",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown('''<style>:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0}[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}[data-testid="stSidebar"]{background:#0b1220}[data-testid="stSidebar"] *{color:#e2e8f0}.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em}.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}.pg-hero h1{color:#fff;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}</style>''',unsafe_allow_html=True)
def money(v): return f"{v:,.2f} TL".replace(",","X").replace(".",",").replace("X",".")
with st.sidebar:
 st.markdown("## ProfitGO"); st.caption("V1.4 • API Finance Development"); st.divider(); st.write("**Trendyol API Merkezi**"); st.caption("Sipariş + Cari Hesap + sipariş bazlı mutabakat")
st.markdown('''<div class="pg-hero"><div>PROFITGO V1.4 • API FINANCE</div><h1>Satışı değil, <em>gerçek finansal sonucu</em> gör.</h1><p>Order API ve Finance API aynı sipariş numarası üzerinde eşleştirilir. Dönem farkları artık doğrudan komisyon alarmı üretmez.</p></div>''',unsafe_allow_html=True)
try:
 seller_id=int(st.secrets["TRENDYOL_SELLER_ID"]); creds=TrendyolCredentials(seller_id,str(st.secrets["TRENDYOL_API_KEY"]),str(st.secrets["TRENDYOL_API_SECRET"]),str(st.secrets.get("TRENDYOL_USER_AGENT",f"{seller_id} - ProfitGO")))
except Exception: st.error("Trendyol API bağlantısı yapılandırılmadı."); st.stop()
st.success(f"API yapılandırması aktif • Satıcı ID: {seller_id}")
c1,c2=st.columns(2)
with c1: start_date=st.date_input("Başlangıç",value=date.today()-timedelta(days=13),max_value=date.today())
with c2: end_date=st.date_input("Bitiş",value=date.today(),min_value=start_date,max_value=date.today())
if (end_date-start_date).days>14: st.warning("15 gün veya daha kısa bir aralık seç."); st.stop()
if st.button("Trendyol'dan sipariş + finans verilerini çek",type="primary",width="stretch"):
 try:
  with st.spinner("Siparişler alınıyor..."): packages=ty.fetch_order_packages(creds,start_date,end_date); lines=ty.packages_to_lines(packages)
  with st.spinner("Cari hesap hareketleri alınıyor..."): settlements=ty.fetch_settlements(creds,start_date,end_date)
  with st.spinner("Kesinti/fatura hareketleri alınıyor..."): deductions=ty.fetch_other_financials(creds,start_date,end_date,"DeductionInvoices")
  st.session_state.v14_api_lines=lines; st.session_state.v14_finance_settlements=settlements; st.session_state.v14_finance_deductions=deductions
  st.success(f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi • {len(deductions):,} kesinti hareketi".replace(",","."))
 except Exception as exc: st.error(f"Entegrasyon hatası: {type(exc).__name__}: {exc}")
if "v14_api_lines" not in st.session_state: st.info("Tarih aralığını seç ve verileri getir."); st.stop()
lines=st.session_state.v14_api_lines.copy(); settlements=st.session_state.get("v14_finance_settlements",pd.DataFrame()).copy(); deductions=st.session_state.get("v14_finance_deductions",pd.DataFrame()).copy()
if lines.empty: st.info("Sipariş bulunamadı."); st.stop()
revenue=float(pd.to_numeric(lines["Teslim Ciro"],errors="coerce").fillna(0).sum()); estimated=float(pd.to_numeric(lines["Tahmini Komisyon"],errors="coerce").fillna(0).sum()); seller_discount=float(pd.to_numeric(lines["Satıcı İndirimi"],errors="coerce").fillna(0).sum()); ty_discount=float(pd.to_numeric(lines["Trendyol İndirimi"],errors="coerce").fillna(0).sum())
fin=ty.settlement_summary(settlements); ded=ty.other_financial_summary(deductions); audit=ty.commission_reconciliation(lines,settlements)
matched_expected=float(audit["Beklenen Komisyon"].sum()) if not audit.empty else 0.; matched_actual=float(audit["Gerçek Komisyon"].sum()) if not audit.empty else 0.; matched_diff=matched_actual-matched_expected; matched_pct=matched_diff/matched_expected*100 if matched_expected else 0.; flagged=int(audit["Durum"].ne("🟢 Uyumlu").sum()) if not audit.empty else 0
st.markdown('<div class="pg-card"><div class="pg-eyebrow">SİPARİŞ BAZLI MUTABAKAT</div><h3>Aynı siparişi aynı siparişle karşılaştırıyoruz</h3><p>Genel dönem toplamları farklı muhasebeleşme tarihleri içerebilir. Alarm yalnızca hem Order API hem Finance API tarafında bulunan siparişler üzerinden üretilir.</p></div>',unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4); k1.metric("Sipariş Ürün Cirosu",money(revenue)); k2.metric("Eşleşen Beklenen Komisyon",money(matched_expected)); k3.metric("Eşleşen Gerçek Komisyon",money(matched_actual),f"Fark {money(matched_diff)}"); k4.metric("Net Kesinti/Fatura",money(ded["net_deduction"]))
if not audit.empty:
 if abs(matched_pct)<.5 and flagged==0: st.success(f"Sipariş bazlı komisyon mutabakatı güçlü • Toplam fark %{matched_pct:.2f} • İncelenecek sipariş yok.")
 else: st.warning(f"Sipariş bazlı toplam fark %{matched_pct:.2f} • {flagged} sipariş incelemeye ayrıldı. Bu alarm yalnızca eşleşen siparişlerden hesaplandı.")
else: st.info("Bu tarih aralığında Order ve Finance API arasında sipariş numarasıyla eşleşen komisyon hareketi bulunamadı.")
a,b,c,d=st.columns(4); a.metric("Dönem Tahmini Komisyon",money(estimated)); b.metric("Dönem Satış Komisyonu",money(fin["sale_commission"])); c.metric("İade Komisyon İptali",money(fin["return_commission"])); d.metric("Cari Hesap Net Geliri",money(fin["seller_revenue_net"]))
st.caption("Dönem toplamları bilgi amaçlıdır; muhasebeleşme tarihi farkı nedeniyle doğrudan alarm üretmez. Trendyol indirimi: "+money(ty_discount)+" • Satıcı indirimi: "+money(seller_discount))
with st.expander("🔎 Sipariş bazlı komisyon denetçisi",expanded=True):
 if audit.empty: st.info("Eşleşen kayıt yok.")
 else:
  st.dataframe(audit,width="stretch",hide_index=True,column_config={"Beklenen Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Gerçek Komisyon":st.column_config.NumberColumn(format="%.2f TL"),"Komisyon Farkı":st.column_config.NumberColumn(format="%.2f TL"),"Fark %":st.column_config.NumberColumn(format="%.2f%%")})
with st.expander("Finans hareketleri"):
 cols=[c for c in ["transactionDate","_sourceTransactionType","orderNumber","barcode","sellerRevenue","commissionRate","commissionAmount","debt","credit"] if c in settlements.columns]; st.dataframe(settlements[cols],width="stretch",hide_index=True) if cols else st.info("Finans hareketi yok.")
with st.expander("Kesinti / fatura hareketleri"):
 cols=[c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in deductions.columns]; st.dataframe(deductions[cols],width="stretch",hide_index=True) if cols else st.info("Kesinti hareketi yok.")
