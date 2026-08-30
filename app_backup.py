import streamlit as st

st.set_page_config(
    page_title="ProfitGO",
    page_icon="📈",
    layout="wide"
)

st.title("ProfitGO")
st.caption("AI Commerce CFO")

st.divider()

st.subheader("CEO Dashboard")
st.write("Temmuz 2026 • C Sehpa")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Satış", "1.397.191 TL")
col2.metric("Satılan Adet", "1.763")
col3.metric("Katkı / Adet", "149 TL")
col4.metric("Katkı Kârı", "≈ 262.700 TL")

st.divider()

st.subheader("🤖 AI CFO Önerisi")

st.success("""
C Sehpa için **899,50 TL fiyat testi** öneriliyor.

Mevcut fiyat: **799,50 TL**

Yeni test fiyatı: **899,50 TL**

Satış adedi yaklaşık **%36'ya kadar düşse bile**
mevcut fiyat seviyesindeki toplam katkı kârı korunabilir.

**Karar: Kontrollü fiyat testine başla.**
""")

st.subheader("Fiyat Laboratuvarı")

st.write("""
799,50 TL → Mevcut fiyat

849,50 TL → İlk optimizasyon seviyesi

**899,50 TL → Önerilen test fiyatı**

949,50 TL → Agresif test
""")

st.info(
    "ProfitGO sadece ne olduğunu göstermez. "
    "Daha fazla kâr için ne yapmanız gerektiğini söyler."
)
