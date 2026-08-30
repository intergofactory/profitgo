import streamlit as st

from excel_upload import render_excel_upload
from trendyol_analysis import render_trendyol_analysis
from reconciliation import render_reconciliation

st.set_page_config(page_title="ProfitGO", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root { --pg-green:#18a66a; --pg-dark:#101828; --pg-muted:#667085; --pg-bg:#f7f9fc; }
[data-testid="stAppViewContainer"] { background: var(--pg-bg); }
.block-container { max-width: 1440px; padding-top: 1.4rem; padding-bottom: 4rem; }
#MainMenu, footer { visibility:hidden; }
[data-testid="stHeader"] { background: transparent; }
.pg-top {display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
.pg-brand {font-size:28px;font-weight:800;color:#101828;letter-spacing:-.8px;}
.pg-brand span {color:#18a66a;}
.pg-pill {font-size:12px;font-weight:700;color:#067647;background:#ecfdf3;border:1px solid #abefc6;padding:7px 11px;border-radius:999px;}
.pg-hero {background:linear-gradient(120deg,#101828,#1d2939);border-radius:22px;padding:32px 36px;color:white;margin:8px 0 22px;box-shadow:0 14px 40px rgba(16,24,40,.12);}
.pg-kicker {font-size:13px;font-weight:700;color:#75e0a7;letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px;}
.pg-title {font-size:36px;line-height:1.12;font-weight:800;letter-spacing:-1.2px;margin:0 0 10px;}
.pg-sub {font-size:16px;color:#d0d5dd;max-width:820px;line-height:1.55;margin:0;}
.pg-card {background:white;border:1px solid #eaecf0;border-radius:16px;padding:18px 20px;box-shadow:0 2px 8px rgba(16,24,40,.04);min-height:112px;}
.pg-card-label {font-size:13px;color:#667085;margin-bottom:10px;}.pg-card-value {font-size:25px;font-weight:800;color:#101828;}.pg-card-note {font-size:12px;color:#98a2b3;margin-top:6px;}
[data-testid="stMetric"] {background:white;border:1px solid #eaecf0;padding:15px 17px;border-radius:14px;box-shadow:0 1px 4px rgba(16,24,40,.03);}
[data-baseweb="tab-list"] {gap:8px;background:white;border:1px solid #eaecf0;padding:7px;border-radius:14px;}
[data-baseweb="tab"] {border-radius:10px;padding:10px 16px;}
[data-baseweb="tab"][aria-selected="true"] {background:#ecfdf3;color:#067647;}
.stButton>button {border-radius:10px;font-weight:700;}
[data-testid="stFileUploader"] {background:white;border:1px dashed #98a2b3;border-radius:16px;padding:8px;}
hr {border-color:#eaecf0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pg-top">
  <div class="pg-brand">Profit<span>GO</span></div>
  <div class="pg-pill">Trendyol Finansal Denetim • V1</div>
</div>
<div class="pg-hero">
  <div class="pg-kicker">E-TİCARET FİNANS KONTROL MERKEZİ</div>
  <div class="pg-title">Trendyol'da paran nereye gidiyor?</div>
  <p class="pg-sub">Sipariş raporunu yükle. ProfitGO komisyon, kargo, iade, ceza ve diğer kesintileri tek ekranda analiz etsin; şüpheli kayıtları incelemeye çıkarsın.</p>
</div>
""", unsafe_allow_html=True)

has_data = "trendyol_orders" in st.session_state
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="pg-card"><div class="pg-card-label">VERİ DURUMU</div><div class="pg-card-value">{"Hazır" if has_data else "Rapor bekleniyor"}</div><div class="pg-card-note">Trendyol Sipariş Kayıtları</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="pg-card"><div class="pg-card-label">DENETİM</div><div class="pg-card-value">Kesinti Avcısı</div><div class="pg-card-note">Mükerrer / olağandışı kesintiler</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="pg-card"><div class="pg-card-label">RİSK KONTROLÜ</div><div class="pg-card-value">Ceza Denetçisi</div><div class="pg-card-note">Şüpheli ceza kayıtları</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="pg-card"><div class="pg-card-label">MUTABAKAT</div><div class="pg-card-value">Net Tutar</div><div class="pg-card-note">ProfitGO ↔ Trendyol karşılaştırması</div></div>', unsafe_allow_html=True)

st.write("")
tab_upload, tab_analysis, tab_recon = st.tabs(["📥 Rapor Yükle", "📊 Finansal Denetim", "🧮 Mutabakat"])
with tab_upload:
    st.markdown("### Analize başla")
    st.caption("Trendyol Satıcı Paneli'nden indirdiğiniz Sipariş Kayıtları Excel dosyasını yükleyin. Dosya işlendiğinde diğer sekmeler otomatik olarak hazır olur.")
    render_excel_upload()
with tab_analysis:
    render_trendyol_analysis()
with tab_recon:
    render_reconciliation()

st.markdown("---")
st.caption("ProfitGO V1 • Trendyol satıcıları için finansal görünürlük ve kesinti denetimi. Sonuçlar finansal kontrol desteğidir; resmi muhasebe kaydı yerine geçmez.")
