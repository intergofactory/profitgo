from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from trendyol_api_v1_4 import TrendyolCredentials, TrendyolApiError, fetch_order_packages, packages_to_lines

st.set_page_config(page_title="ProfitGO V1.4 - API Kârlılık Merkezi", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#0b1220}[data-testid="stSidebar"] *{color:#e2e8f0}
.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 2px 8px rgba(15,23,42,.035);margin-bottom:14px}.pg-card h3{font-size:20px;margin:0 0 6px}.pg-card p{font-size:12px;color:#64748b;line-height:1.6;margin:0}.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em;margin-bottom:6px}
.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}.pg-hero h1{color:#fff;margin:5px 0 8px;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}.pg-hero p{color:#cbd5e1;max-width:850px;line-height:1.6}
[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}.stButton>button{border-radius:10px;font-weight:700}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ProfitGO")
    st.caption("V1.4 • API Development")
    st.divider()
    st.write("**Trendyol API Merkezi**")
    st.caption("Excel yükleme kaldırıldı. Veriler Trendyol Partner API üzerinden çekilir.")

st.markdown('''<div class="pg-hero"><div style="font-size:10px;font-weight:800;letter-spacing:.14em;color:#6ee7b7">PROFITGO V1.4 • API</div><h1>Excel yok. <em>Trendyol'a doğrudan bağlan.</em></h1><p>Sipariş ve ürün hareketlerini Trendyol API üzerinden çek. ProfitGO ürün bazında satış, indirim, komisyon, KDV ve maliyet sinyallerini otomatik oluşturur.</p></div>''', unsafe_allow_html=True)

try:
    seller_id = int(st.secrets["TRENDYOL_SELLER_ID"])
    api_key = str(st.secrets["TRENDYOL_API_KEY"])
    api_secret = str(st.secrets["TRENDYOL_API_SECRET"])
    user_agent = str(st.secrets.get("TRENDYOL_USER_AGENT", f"{seller_id} - ProfitGO"))
    creds = TrendyolCredentials(seller_id=seller_id, api_key=api_key, api_secret=api_secret, user_agent=user_agent)
    configured = True
except Exception:
    creds = None
    configured = False

if not configured:
    st.error("Trendyol API bağlantısı henüz yapılandırılmadı. Streamlit Secrets içine TRENDYOL_SELLER_ID, TRENDYOL_API_KEY ve TRENDYOL_API_SECRET eklenmeli.")
    st.stop()

st.success(f"API yapılandırması bulundu • Satıcı ID: {seller_id}")

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Başlangıç", value=date.today() - timedelta(days=13), max_value=date.today())
with c2:
    end_date = st.date_input("Bitiş", value=date.today(), min_value=start_date, max_value=date.today())

if (end_date - start_date).days > 13:
    st.warning("Trendyol sipariş servisi tek sorguda en fazla iki haftalık tarih aralığına izin verir. 14 gün veya daha kısa bir aralık seç.")
    st.stop()

if st.button("Trendyol'dan verileri çek", type="primary", width="stretch"):
    with st.spinner("Trendyol API'den siparişler alınıyor..."):
        try:
            packages = fetch_order_packages(creds, start_date, end_date)
            lines = packages_to_lines(packages)
            st.session_state.v14_api_packages = packages
            st.session_state.v14_api_lines = lines
            st.session_state.v14_api_period = (start_date, end_date)
            st.success(f"{len(packages):,} paket ve {len(lines):,} ürün satırı alındı.".replace(",", "."))
        except TrendyolApiError as exc:
            st.error(str(exc))

if "v14_api_lines" in st.session_state:
    df = st.session_state.v14_api_lines.copy()
    if df.empty:
        st.info("Seçilen dönemde sipariş bulunamadı.")
        st.stop()

    revenue = float(pd.to_numeric(df["Teslim Ciro"], errors="coerce").fillna(0).sum())
    seller_discount = float(pd.to_numeric(df["Satıcı İndirimi"], errors="coerce").fillna(0).sum())
    ty_discount = float(pd.to_numeric(df["Trendyol İndirimi"], errors="coerce").fillna(0).sum())
    estimated_commission = float(pd.to_numeric(df["Tahmini Komisyon"], errors="coerce").fillna(0).sum())

    a,b,c,d = st.columns(4)
    a.metric("API Ürün Satırı", f"{len(df):,}".replace(",", "."))
    b.metric("Net Ürün Cirosu", f"{revenue:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
    c.metric("Satıcı İndirimi", f"{seller_discount:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
    d.metric("Tahmini Komisyon", f"{estimated_commission:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown('<div class="pg-card"><div class="pg-eyebrow">API VERİSİ</div><h3>Ürün bazlı sipariş hareketleri</h3><p>Bu ekran doğrudan Trendyol Order V2 API yanıtından oluşturulur. Komisyon burada API satırındaki oran üzerinden tahmini gösterilir; gerçek finansal mutabakat için fatura/kesinti servisleri bir sonraki API katmanında bağlanacaktır.</p></div>', unsafe_allow_html=True)

    display_cols = [c for c in ["Sipariş No","Sipariş Statüsü","Model Kodu","Barkod","Ürün Adı","Ürün Adedi","Birim Net Fiyat","Teslim Ciro","Satıcı İndirimi","Trendyol İndirimi","Komisyon Oranı %","Tahmini Komisyon","KDV Oranı %"] if c in df.columns]
    st.dataframe(df[display_cols], width="stretch", hide_index=True)

    st.caption(f"Trendyol tarafından karşılanan indirim: {ty_discount:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
