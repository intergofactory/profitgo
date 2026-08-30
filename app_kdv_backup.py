import streamlit as st

# ==========================================
# PROFITGO — KDV UYUMLU HESAPLAMA MOTORU
# ==========================================

PRODUCT_NAME = "C Sehpa"

# KDV DAHİL VERİLER
current_price_gross = 799.50
unit_cost_gross = 370.00

# Vergi oranları
sales_vat_rate = 0.20
purchase_vat_rate = 0.20

# Trendyol giderleri
avg_shipping_gross = 124.05
avg_discount = 34.70
other_cost_gross = 0.51

commission_rate = 0.1382
platform_rate = 0.0135

monthly_units = 1763


# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================

def remove_vat(gross, vat_rate):
    return gross / (1 + vat_rate)


def vat_amount(gross, vat_rate):
    return gross - remove_vat(gross, vat_rate)


# ==========================================
# KDV MOTORU
# ==========================================

def calculate_unit(price_gross):

    # Satış
    sale_net = remove_vat(
        price_gross,
        sales_vat_rate
    )

    output_vat = vat_amount(
        price_gross,
        sales_vat_rate
    )

    # Ürün maliyeti
    product_cost_net = remove_vat(
        unit_cost_gross,
        purchase_vat_rate
    )

    product_input_vat = vat_amount(
        unit_cost_gross,
        purchase_vat_rate
    )

    # Kargo
    shipping_net = remove_vat(
        avg_shipping_gross,
        sales_vat_rate
    )

    shipping_input_vat = vat_amount(
        avg_shipping_gross,
        sales_vat_rate
    )

    # Diğer gider
    other_cost_net = remove_vat(
        other_cost_gross,
        sales_vat_rate
    )

    other_input_vat = vat_amount(
        other_cost_gross,
        sales_vat_rate
    )

    # Komisyon ve platform bedeli
    commission_gross = (
        price_gross * commission_rate
    )

    commission_net = remove_vat(
        commission_gross,
        sales_vat_rate
    )

    commission_input_vat = vat_amount(
        commission_gross,
        sales_vat_rate
    )

    platform_gross = (
        price_gross * platform_rate
    )

    platform_net = remove_vat(
        platform_gross,
        sales_vat_rate
    )

    platform_input_vat = vat_amount(
        platform_gross,
        sales_vat_rate
    )

    # Katkı kârı KDV HARİÇ bazda hesaplanır
    contribution = (
        sale_net
        - product_cost_net
        - shipping_net
        - avg_discount
        - other_cost_net
        - commission_net
        - platform_net
    )

    total_input_vat = (
        product_input_vat
        + shipping_input_vat
        + other_input_vat
        + commission_input_vat
        + platform_input_vat
    )

    net_vat_payable = (
        output_vat - total_input_vat
    )

    return {
        "price_gross": price_gross,
        "sale_net": sale_net,
        "output_vat": output_vat,
        "product_cost_net": product_cost_net,
        "commission_net": commission_net,
        "shipping_net": shipping_net,
        "platform_net": platform_net,
        "input_vat": total_input_vat,
        "net_vat_payable": net_vat_payable,
        "contribution": contribution
    }


def monthly_contribution(price, units):
    return (
        calculate_unit(price)["contribution"]
        * units
    )


def max_sales_drop_rate(new_price):

    current_profit = monthly_contribution(
        current_price_gross,
        monthly_units
    )

    new_unit_profit = calculate_unit(
        new_price
    )["contribution"]

    if new_unit_profit <= 0:
        return 0

    break_even_units = (
        current_profit / new_unit_profit
    )

    drop_rate = (
        1 - break_even_units / monthly_units
    )

    return max(0, drop_rate)


def simulate_price(price, sales_drop_rate=0):

    estimated_units = (
        monthly_units * (1 - sales_drop_rate)
    )

    unit = calculate_unit(price)

    total_contribution = (
        unit["contribution"]
        * estimated_units
    )

    return {
        "price": price,
        "units": estimated_units,
        "unit": unit,
        "total_contribution": total_contribution
    }


# ==========================================
# SENARYOLAR
# ==========================================

current = simulate_price(
    current_price_gross
)

recommended_price = 899.50

recommended = simulate_price(
    recommended_price
)

max_drop = max_sales_drop_rate(
    recommended_price
)

recommended_10_drop = simulate_price(
    recommended_price,
    0.10
)

extra_profit_10_drop = (
    recommended_10_drop["total_contribution"]
    - current["total_contribution"]
)


# ==========================================
# STREAMLIT
# ==========================================

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

col1.metric(
    "Satış Fiyatı (KDV Dahil)",
    f"{current_price_gross:,.2f} TL"
)

col2.metric(
    "Satılan Adet",
    f"{monthly_units:,}"
)

col3.metric(
    "Gerçek Katkı / Adet",
    f"{current['unit']['contribution']:,.2f} TL"
)

col4.metric(
    "Aylık Katkı Kârı",
    f"{current['total_contribution']:,.0f} TL"
)

st.divider()

st.subheader("🧾 KDV Analizi")

v1, v2, v3, v4 = st.columns(4)

v1.metric(
    "KDV Hariç Satış",
    f"{current['unit']['sale_net']:,.2f} TL"
)

v2.metric(
    "Hesaplanan KDV",
    f"{current['unit']['output_vat']:,.2f} TL"
)

v3.metric(
    "İndirilecek KDV",
    f"{current['unit']['input_vat']:,.2f} TL"
)

v4.metric(
    "Net KDV Etkisi / Adet",
    f"{current['unit']['net_vat_payable']:,.2f} TL"
)

st.divider()

st.subheader("🤖 AI CFO Önerisi")

st.success(
    f"""
**{PRODUCT_NAME} için {recommended_price:,.2f} TL kontrollü fiyat testi öneriliyor.**

Mevcut fiyat:
**{current_price_gross:,.2f} TL**

Mevcut gerçek katkı / adet:
**{current['unit']['contribution']:,.2f} TL**

Test fiyatı:
**{recommended_price:,.2f} TL**

Yeni katkı / adet:
**{recommended['unit']['contribution']:,.2f} TL**

Satış adedi yaklaşık **%{max_drop * 100:.1f}**
oranına kadar düşse bile mevcut toplam katkı kârı korunabilir.

Satış adedi %10 düşerse tahmini aylık katkı farkı:

**{extra_profit_10_drop:+,.0f} TL**

### ProfitGO Kararı

**{recommended_price:,.2f} TL kontrollü fiyat testine başla.**
"""
)

st.divider()

st.subheader("🧪 Fiyat Laboratuvarı")

prices = [
    799.50,
    849.50,
    899.50,
    949.50
]

for price in prices:

    scenario = simulate_price(price)
    unit = scenario["unit"]

    drop = max_sales_drop_rate(price)

    st.write(
        f"""
### {price:,.2f} TL

KDV hariç satış:
**{unit['sale_net']:,.2f} TL**

Katkı / adet:
**{unit['contribution']:,.2f} TL**

Aylık katkı:
**{scenario['total_contribution']:,.0f} TL**

Tolere edilebilir satış kaybı:
**%{drop * 100:.1f}**
"""
    )

st.divider()

st.info(
    "ProfitGO satış fiyatını, maliyetleri, pazar yeri "
    "kesintilerini ve KDV etkisini aynı ekonomik bazda "
    "değerlendirerek aksiyon üretir."
)
