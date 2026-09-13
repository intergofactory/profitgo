from __future__ import annotations

from datetime import date, timedelta
import importlib

import pandas as pd
import streamlit as st
import trendyol_api_v1_4 as ty

# Streamlit Community Cloud can keep an already-imported module in memory across
# rapid branch deploys. Reload it so the UI and API layer always use the same commit.
ty = importlib.reload(ty)
TrendyolCredentials = ty.TrendyolCredentials
TrendyolApiError = ty.TrendyolApiError

st.set_page_config(page_title="ProfitGO V1.4 - API Finans Merkezi", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--bg:#f4f7fb;--ink:#0b1220;--line:#e5eaf0}
[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--ink)}
.block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#0b1220}[data-testid="stSidebar"] *{color:#e2e8f0}
.pg-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 2px 8px rgba(15,23,42,.035);margin-bottom:14px}
.pg-card h3{font-size:20px;margin:0 0 6px}.pg-card p{font-size:12px;color:#64748b;line-height:1.6;margin:0}
.pg-eyebrow{font-size:9px;font-weight:800;color:#059669;letter-spacing:.13em;margin-bottom:6px}
.pg-hero{background:linear-gradient(125deg,#09111f,#101b30 62%,#073d32);border-radius:24px;padding:32px 38px;color:#fff;margin-bottom:16px}
.pg-hero h1{color:#fff;margin:5px 0 8px;font-size:38px}.pg-hero em{font-style:normal;color:#6ee7b7}.pg-hero p{color:#cbd5e1;max-width:900px;line-height:1.6}
[data-testid="stMetric"],[data-testid="stDataFrame"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px}
.stButton>button{border-radius:10px;font-weight:700}
</style>
""", unsafe_allow_html=True)


def money(value: float) -> str:
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


with st.sidebar:
    st.markdown("## ProfitGO")
    st.caption("V1.4 • API Finance Development")
    st.divider()
    st.write("**Trendyol API Merkezi**")
    st.caption("Sipariş + Cari Hesap Ekstresi API entegrasyonu")

st.markdown('''<div class="pg-hero"><div style="font-size:10px;font-weight:800;letter-spacing:.14em;color:#6ee7b7">PROFITGO V1.4 • API FINANCE</div><h1>Satışı değil, <em>gerçek finansal sonucu</em> gör.</h1><p>ProfitGO siparişleri Order V2 API'den, gerçek komisyon ve cari hesap hareketlerini Trendyol Finance API'den çeker. Tahmini kesinti ile gerçekleşen kesintiyi aynı ekranda karşılaştırır.</p></div>''', unsafe_allow_html=True)

try:
    seller_id = int(st.secrets["TRENDYOL_SELLER_ID"])
    api_key = str(st.secrets["TRENDYOL_API_KEY"])
    api_secret = str(st.secrets["TRENDYOL_API_SECRET"])
    user_agent = str(st.secrets.get("TRENDYOL_USER_AGENT", f"{seller_id} - ProfitGO"))
    creds = TrendyolCredentials(seller_id=seller_id, api_key=api_key, api_secret=api_secret, user_agent=user_agent)
except Exception:
    st.error("Trendyol API bağlantısı yapılandırılmadı. Streamlit Secrets kontrol edilmeli.")
    st.stop()

st.success(f"API yapılandırması aktif • Satıcı ID: {seller_id}")

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Başlangıç", value=date.today() - timedelta(days=13), max_value=date.today())
with c2:
    end_date = st.date_input("Bitiş", value=date.today(), min_value=start_date, max_value=date.today())

if (end_date - start_date).days > 14:
    st.warning("Finans servisi tek sorguda en fazla 15 günlük tarih aralığına izin verir. 15 gün veya daha kısa bir aralık seç.")
    st.stop()

if st.button("Trendyol'dan sipariş + finans verilerini çek", type="primary", width="stretch"):
    try:
        with st.spinner("1/3 Siparişler Trendyol Order V2 API'den alınıyor..."):
            packages = ty.fetch_order_packages(creds, start_date, end_date)
            lines = ty.packages_to_lines(packages)

        with st.spinner("2/3 Gerçek komisyon ve cari hesap hareketleri alınıyor..."):
            settlements = ty.fetch_settlements(creds, start_date, end_date)

        with st.spinner("3/3 Trendyol hizmet/kesinti faturaları alınıyor..."):
            deductions = ty.fetch_other_financials(creds, start_date, end_date, transaction_type="DeductionInvoices")

        st.session_state.v14_api_packages = packages
        st.session_state.v14_api_lines = lines
        st.session_state.v14_finance_settlements = settlements
        st.session_state.v14_finance_deductions = deductions
        st.session_state.v14_api_period = (start_date, end_date)
        st.success(
            f"{len(packages):,} paket • {len(lines):,} ürün satırı • {len(settlements):,} finans hareketi • {len(deductions):,} kesinti/fatura hareketi alındı."
            .replace(",", ".")
        )
    except TrendyolApiError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Beklenmeyen entegrasyon hatası: {type(exc).__name__}: {exc}")

if "v14_api_lines" not in st.session_state:
    st.info("Tarih aralığını seç ve canlı sipariş + finans verilerini getir.")
    st.stop()

lines = st.session_state.v14_api_lines.copy()
settlements = st.session_state.get("v14_finance_settlements", pd.DataFrame()).copy()
deductions = st.session_state.get("v14_finance_deductions", pd.DataFrame()).copy()

if lines.empty:
    st.info("Seçilen dönemde sipariş bulunamadı.")
    st.stop()

revenue = float(pd.to_numeric(lines["Teslim Ciro"], errors="coerce").fillna(0).sum())
seller_discount = float(pd.to_numeric(lines["Satıcı İndirimi"], errors="coerce").fillna(0).sum())
ty_discount = float(pd.to_numeric(lines["Trendyol İndirimi"], errors="coerce").fillna(0).sum())
estimated_commission = float(pd.to_numeric(lines["Tahmini Komisyon"], errors="coerce").fillna(0).sum())

fin = ty.settlement_summary(settlements)
ded = ty.other_financial_summary(deductions)
actual_commission = fin["commission_net"]
commission_diff = actual_commission - estimated_commission
commission_diff_pct = (commission_diff / estimated_commission * 100.0) if estimated_commission else 0.0

st.markdown('<div class="pg-card"><div class="pg-eyebrow">CANLI FİNANS ÖZETİ</div><h3>Order API + Finance API mutabakatı</h3><p>Sipariş ekranındaki tahmini komisyon ile Cari Hesap Ekstresi servisindeki gerçekleşen komisyon ayrı tutulur. Böylece fark doğrudan görülebilir.</p></div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sipariş Ürün Cirosu", money(revenue))
k2.metric("Tahmini Komisyon", money(estimated_commission))
k3.metric("Gerçek Net Komisyon", money(actual_commission), f"Fark {money(commission_diff)}")
k4.metric("Net Kesinti/Fatura", money(ded["net_deduction"]))

if abs(commission_diff_pct) < 0.5:
    st.success(f"Komisyon mutabakatı güçlü: tahmini ve gerçekleşen komisyon farkı %{commission_diff_pct:.2f}.")
elif abs(commission_diff_pct) < 2:
    st.warning(f"Komisyon farkı %{commission_diff_pct:.2f}. Dönem/zamanlama etkisi olabilir; detay kontrolü önerilir.")
else:
    st.error(f"Komisyon farkı %{commission_diff_pct:.2f}. ProfitGO bu farkı incelemeye ayırdı.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cari Hesap Net Geliri", money(fin["seller_revenue_net"]))
m2.metric("Satış Komisyonu", money(fin["sale_commission"]))
m3.metric("İade Komisyon İptali", money(fin["return_commission"]))
m4.metric("Satıcı İndirimi", money(seller_discount))

st.caption(f"Trendyol tarafından karşılanan indirim: {money(ty_discount)}")

with st.expander("Finans hareketleri", expanded=False):
    if settlements.empty:
        st.info("Bu dönemde Cari Hesap Ekstresi finans hareketi dönmedi.")
    else:
        cols = [c for c in ["transactionDate","_sourceTransactionType","transactionType","description","orderNumber","barcode","sellerRevenue","commissionRate","commissionAmount","debt","credit","paymentOrderId"] if c in settlements.columns]
        st.dataframe(settlements[cols], width="stretch", hide_index=True)

with st.expander("Kesinti / fatura hareketleri", expanded=False):
    if deductions.empty:
        st.info("Bu dönemde DeductionInvoices hareketi dönmedi.")
    else:
        cols = [c for c in ["transactionDate","transactionType","transactionSubType","description","debt","credit","id","paymentOrderId"] if c in deductions.columns]
        st.dataframe(deductions[cols], width="stretch", hide_index=True)

with st.expander("Ürün bazlı sipariş hareketleri", expanded=False):
    display_cols = [c for c in ["Sipariş No","Sipariş Statüsü","Model Kodu","Barkod","Ürün Adı","Ürün Adedi","Birim Net Fiyat","Teslim Ciro","Satıcı İndirimi","Trendyol İndirimi","Komisyon Oranı %","Tahmini Komisyon","KDV Oranı %"] if c in lines.columns]
    st.dataframe(lines[display_cols], width="stretch", hide_index=True)

st.markdown('<div class="pg-card"><div class="pg-eyebrow">SIRADAKİ KATMAN</div><h3>Gerçek kâr motoru</h3><p>Bir sonraki adımda ürün maliyetlerini kalıcı ürün kartlarına bağlayıp KDV ayrıştırması, kargo faturası ve platform hizmet bedeli detaylarını sipariş/model bazında dağıtacağız.</p></div>', unsafe_allow_html=True)
