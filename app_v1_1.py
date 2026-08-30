import streamlit as st
import pandas as pd

from excel_upload_v1_1 import render_excel_upload_v11
from trendyol_analysis import render_trendyol_analysis
from reconciliation import render_reconciliation

st.set_page_config(
    page_title="ProfitGO — Trendyol Finans Kontrol Merkezi",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --pg-bg:#f5f7fb; --pg-surface:#ffffff; --pg-ink:#0b1220; --pg-muted:#64748b;
  --pg-line:#e6eaf0; --pg-green:#10b981; --pg-green-dark:#047857; --pg-navy:#0b1220;
  --pg-soft:#ecfdf5; --pg-warn:#f59e0b; --pg-red:#ef4444;
}
html, body, [class*="css"] { font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
[data-testid="stAppViewContainer"] { background:var(--pg-bg); color:var(--pg-ink); }
[data-testid="stHeader"] { background:rgba(245,247,251,.85); backdrop-filter: blur(10px); }
.block-container { max-width:1500px; padding-top:1.05rem; padding-bottom:4rem; }
#MainMenu, footer { visibility:hidden; }
h1,h2,h3 { letter-spacing:-.035em; color:var(--pg-ink); }
hr { border-color:var(--pg-line)!important; }

.pg-nav {display:flex;align-items:center;justify-content:space-between;padding:8px 2px 18px;}
.pg-logo {display:flex;align-items:center;gap:10px;font-size:25px;font-weight:800;letter-spacing:-.8px;color:var(--pg-ink);}
.pg-logo-mark {width:32px;height:32px;border-radius:10px;background:linear-gradient(145deg,#10b981,#047857);display:grid;place-items:center;color:#fff;font-weight:900;box-shadow:0 8px 18px rgba(16,185,129,.22)}
.pg-logo b {color:var(--pg-green-dark);}
.pg-nav-right {display:flex;align-items:center;gap:10px;}
.pg-status {display:flex;align-items:center;gap:7px;padding:8px 11px;background:#fff;border:1px solid var(--pg-line);border-radius:999px;font-size:12px;font-weight:600;color:#475569;}
.pg-live {width:7px;height:7px;border-radius:50%;background:#10b981;box-shadow:0 0 0 4px #d1fae5;}
.pg-version {padding:8px 11px;background:#0b1220;color:#fff;border-radius:999px;font-size:12px;font-weight:700;}

.pg-hero {position:relative;overflow:hidden;background:linear-gradient(125deg,#09111f 0%,#101b30 62%,#073d32 120%);border:1px solid rgba(255,255,255,.06);border-radius:26px;padding:38px 42px;color:white;box-shadow:0 20px 50px rgba(15,23,42,.14);}
.pg-hero:after {content:"";position:absolute;width:430px;height:430px;border-radius:50%;right:-150px;top:-220px;background:radial-gradient(circle,rgba(16,185,129,.38),rgba(16,185,129,0) 68%);}
.pg-hero-grid {position:relative;z-index:2;display:grid;grid-template-columns:1.55fr .75fr;gap:30px;align-items:center;}
.pg-kicker {font-size:12px;font-weight:800;letter-spacing:.13em;color:#6ee7b7;text-transform:uppercase;margin-bottom:12px;}
.pg-title {font-size:42px;line-height:1.06;font-weight:800;letter-spacing:-1.8px;max-width:880px;margin:0 0 13px;}
.pg-title em {font-style:normal;color:#6ee7b7;}
.pg-sub {font-size:15px;line-height:1.65;color:#cbd5e1;max-width:760px;margin:0;}
.pg-trust {display:flex;gap:20px;margin-top:22px;color:#cbd5e1;font-size:12px;}
.pg-trust span {display:flex;align-items:center;gap:7px;}
.pg-hero-panel {background:rgba(255,255,255,.075);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:18px;backdrop-filter:blur(5px);}
.pg-hero-panel .label {font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:700;}
.pg-hero-panel .big {font-size:25px;font-weight:800;margin:6px 0 2px;}
.pg-hero-panel .small {font-size:12px;color:#94a3b8;}
.pg-mini-row {display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,.09);margin-top:14px;padding-top:12px;font-size:12px;color:#cbd5e1;}

.pg-kpis {display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 8px;}
.pg-kpi {background:#fff;border:1px solid var(--pg-line);border-radius:17px;padding:17px 18px;box-shadow:0 2px 8px rgba(15,23,42,.035);}
.pg-kpi-top {display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;}
.pg-kpi-icon {width:34px;height:34px;border-radius:10px;background:#f0fdf4;display:grid;place-items:center;font-size:16px;}
.pg-kpi-badge {font-size:10px;font-weight:700;color:#047857;background:#ecfdf5;border-radius:99px;padding:4px 7px;}
.pg-kpi-label {font-size:12px;color:#64748b;font-weight:600;}
.pg-kpi-value {font-size:23px;letter-spacing:-.8px;font-weight:800;color:#0b1220;margin-top:4px;}
.pg-kpi-note {font-size:11px;color:#94a3b8;margin-top:5px;}

.pg-section-head {display:flex;align-items:flex-start;justify-content:space-between;gap:24px;background:#fff;border:1px solid var(--pg-line);border-radius:18px;padding:21px 22px;margin:5px 0 14px;}
.pg-section-head h2 {font-size:22px;margin:3px 0 6px;}.pg-section-head p {font-size:13px;color:#64748b;margin:0;max-width:780px;line-height:1.55;}
.pg-eyebrow {font-size:10px;font-weight:800;color:#059669;letter-spacing:.12em;}.pg-secure {font-size:11px;color:#475569;background:#f8fafc;border:1px solid #e2e8f0;border-radius:999px;padding:8px 10px;white-space:nowrap;}
.pg-upload-hint {display:flex;gap:13px;align-items:center;background:#fff;border:1px dashed #cbd5e1;border-radius:15px;padding:16px 18px;margin-top:8px;color:#334155;}.pg-upload-hint span{font-size:12px;color:#94a3b8}.pg-upload-icon{width:34px;height:34px;border-radius:10px;background:#ecfdf5;color:#047857;font-size:21px;display:grid;place-items:center;font-weight:700}
.pg-success {display:flex;gap:12px;align-items:center;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:13px 15px;margin:10px 0 14px;color:#065f46;}.pg-success span{font-size:12px;color:#047857}.pg-success-dot{width:28px;height:28px;border-radius:50%;background:#10b981;color:#fff;display:grid;place-items:center;font-weight:800}

[data-baseweb="tab-list"] {gap:5px;background:#fff;border:1px solid var(--pg-line);padding:6px;border-radius:14px;box-shadow:0 1px 3px rgba(15,23,42,.03);}
[data-baseweb="tab"] {height:42px;border-radius:9px;padding:0 17px;font-weight:600;color:#64748b;}
[data-baseweb="tab"][aria-selected="true"] {background:#0b1220!important;color:#fff!important;}
[data-testid="stMetric"] {background:#fff;border:1px solid var(--pg-line);padding:15px 16px;border-radius:14px;box-shadow:0 1px 4px rgba(15,23,42,.03);}
[data-testid="stMetricLabel"] {color:#64748b;}
[data-testid="stMetricValue"] {font-weight:800;letter-spacing:-.6px;}
[data-testid="stFileUploader"] {background:#fff;border:1px solid var(--pg-line);border-radius:16px;padding:9px;}
[data-testid="stFileUploaderDropzone"] {background:#f8fafc;border-radius:12px;border-color:#cbd5e1;}
[data-testid="stDataFrame"] {border:1px solid var(--pg-line);border-radius:14px;overflow:hidden;background:#fff;}
.stAlert {border-radius:13px;}
.stButton>button {border-radius:10px;font-weight:700;border-color:#dbe2ea;}
[data-testid="stExpander"] {background:#fff;border:1px solid var(--pg-line);border-radius:12px;}

.pg-foot {display:flex;justify-content:space-between;gap:20px;color:#94a3b8;font-size:11px;padding:20px 2px 0;}
@media(max-width:900px){.pg-hero-grid{grid-template-columns:1fr}.pg-kpis{grid-template-columns:1fr 1fr}.pg-title{font-size:34px}.pg-hero-panel{display:none}.pg-section-head{display:block}.pg-secure{display:inline-block;margin-top:12px}}
</style>
""", unsafe_allow_html=True)


def _num(df, col):
    if col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _money(v):
    return f"{abs(v):,.0f} TL".replace(",", ".")

has_data = "trendyol_orders" in st.session_state
if has_data:
    df = st.session_state["trendyol_orders"]
    status = df["Sipariş Statüsü"].astype(str).str.strip() if "Sipariş Statüsü" in df.columns else pd.Series([""]*len(df))
    delivered = df[status.eq("Teslim Edildi")]
    order_count = len(df)
    delivered_count = int(status.eq("Teslim Edildi").sum())
    revenue = _num(delivered, "Sipariş Tutarı")
    net = _num(df, "Net Tutar")
    penalty = _num(df, "Ceza Bedeli")
else:
    order_count = delivered_count = 0
    revenue = net = penalty = 0

st.markdown('''
<div class="pg-nav">
  <div class="pg-logo"><div class="pg-logo-mark">G</div>Profit<b>GO</b></div>
  <div class="pg-nav-right"><div class="pg-status"><span class="pg-live"></span>Denetim motoru aktif</div><div class="pg-version">V1.1</div></div>
</div>
''', unsafe_allow_html=True)

status_text = "Rapor analiz için hazır" if has_data else "Yeni analiz başlat"
file_text = st.session_state.get("profitgo_filename", "Trendyol Sipariş Kayıtları") if has_data else "Excel raporunu yükleyerek başla"
st.markdown(f'''
<div class="pg-hero">
  <div class="pg-hero-grid">
    <div>
      <div class="pg-kicker">TRENDYOL FİNANS KONTROL MERKEZİ</div>
      <div class="pg-title">Paranın nereye gittiğini <em>gör.</em><br>Şüpheli kesintiyi <em>yakala.</em></div>
      <p class="pg-sub">Komisyon, kargo, iade, platform bedeli ve cezaları tek ekranda denetle. ProfitGO, sipariş raporunu finansal sinyallere dönüştürür ve incelemen gereken kayıtları öne çıkarır.</p>
      <div class="pg-trust"><span>✓ Otomatik mutabakat</span><span>✓ Ceza denetimi</span><span>✓ Kesinti analizi</span></div>
    </div>
    <div class="pg-hero-panel">
      <div class="label">ÇALIŞMA ALANI</div><div class="big">{status_text}</div><div class="small">{file_text}</div>
      <div class="pg-mini-row"><span>Kaynak</span><strong>Trendyol</strong></div>
      <div class="pg-mini-row"><span>Motor</span><strong>Finansal Denetim V1.1</strong></div>
    </div>
  </div>
</div>
''', unsafe_allow_html=True)

kpis = [
    ("◫", "Sipariş", f"{order_count:,}".replace(",", ".") if has_data else "—", "Rapordaki toplam kayıt"),
    ("✓", "Teslim edilen", f"{delivered_count:,}".replace(",", ".") if has_data else "—", "Tamamlanan siparişler"),
    ("↗", "Teslim edilen ciro", _money(revenue) if has_data else "—", "Brüt sipariş tutarı"),
    ("◎", "Net finansal tutar", _money(net) if has_data else "—", (f"Ceza: {_money(penalty)}" if has_data else "Analiz sonrası hesaplanır")),
]
html = '<div class="pg-kpis">'
for icon,label,value,note in kpis:
    html += f'<div class="pg-kpi"><div class="pg-kpi-top"><div class="pg-kpi-icon">{icon}</div><div class="pg-kpi-badge">CANLI</div></div><div class="pg-kpi-label">{label}</div><div class="pg-kpi-value">{value}</div><div class="pg-kpi-note">{note}</div></div>'
html += '</div>'
st.markdown(html, unsafe_allow_html=True)

st.write("")
tab_upload, tab_analysis, tab_recon = st.tabs(["01  Rapor Yükle", "02  Finansal Denetim", "03  Mutabakat"])
with tab_upload:
    render_excel_upload_v11()
with tab_analysis:
    render_trendyol_analysis()
with tab_recon:
    render_reconciliation()

st.markdown('''<div class="pg-foot"><span>ProfitGO V1.1 • Trendyol satıcıları için finansal görünürlük</span><span>Finansal kontrol desteğidir; resmi muhasebe kaydı yerine geçmez.</span></div>''', unsafe_allow_html=True)
