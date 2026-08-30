from __future__ import annotations

import pandas as pd
import streamlit as st

from product_profitability_v1_4 import render_product_profitability_v14

st.set_page_config(
    page_title="ProfitGO V1.4 - Kârlılık Merkezi",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0;--green:#10b981}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}
.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#0b1220}
[data-testid="stSidebar"] *{color:#e2e8f0}
.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 2px 8px rgba(15,23,42,.035);margin-bottom:14px}
.pg-card h3{font-size:20px;margin:0 0 6px}.pg-card p{font-size:12px;color:#64748b;line-height:1.6;margin:0}
.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em;margin-bottom:6px}
.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}
.pg-hero h1{color:#fff;margin:5px 0 8px;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}.pg-hero p{color:#cbd5e1;max-width:850px;line-height:1.6}
[data-testid="stMetric"],[data-testid="stDataFrame"],[data-testid="stFileUploader"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}
.stButton>button{border-radius:10px;font-weight:700}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ProfitGO")
    st.caption("V1.4 • Development")
    st.divider()
    st.write("**Kârlılık Merkezi**")
    st.caption("Bu dal canlı V1.3'ten tamamen ayrıdır.")

st.markdown('''<div class="pg-hero"><div style="font-size:10px;font-weight:800;letter-spacing:.14em;color:#6ee7b7">PROFITGO V1.4</div><h1>Ürün bazında <em>gerçek kârı</em> gör.</h1><p>Trendyol finansal netini ürün maliyetleriyle birleştir. Zarar eden ve düşük marjlı ürünleri otomatik öne çıkar.</p></div>''', unsafe_allow_html=True)

uploaded = st.file_uploader("Trendyol Sipariş Kayıtları Excel", type=["xlsx", "xls"], key="v14_test_upload")

if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)
        st.session_state["v14_test_df"] = df
        st.success(f"{len(df):,} kayıt yüklendi.".replace(",", "."))
    except Exception as exc:
        st.error(f"Excel okunamadı: {exc}")

if "v14_test_df" in st.session_state:
    render_product_profitability_v14(st.session_state["v14_test_df"])
else:
    st.info("V1.4 kârlılık motorunu test etmek için Trendyol Sipariş Kayıtları raporunu yükle.")
