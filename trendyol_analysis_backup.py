import streamlit as st
import pandas as pd

def money(value):
    return f"{value:,.2f} TL"

def safe_sum(df, column):
    if column not in df.columns:
        return 0.0
    return float(
        pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0).sum()
    )

def render_trendyol_analysis():
    st.divider()
    st.subheader("📊 Trendyol Finansal Analiz")

    if "trendyol_orders" not in st.session_state:
        st.info("Önce Sipariş Kayıtları Excel dosyasını yükleyin.")
        return

    df = st.session_state["trendyol_orders"].copy()

    statuses = (
        df["Sipariş Statüsü"].astype(str).str.strip()
        if "Sipariş Statüsü" in df.columns
        else pd.Series([""] * len(df))
    )

    delivered = df[statuses.eq("Teslim Edildi")].copy()

    total_orders = len(df)
    delivered_orders = len(delivered)
    returned_orders = int(statuses.eq("İade Edildi").sum())
    cancelled_orders = int(statuses.eq("İptal Edildi").sum())

    units = safe_sum(delivered, "Ürün Adedi")
    revenue = safe_sum(delivered, "Sipariş Tutarı")
    commission = safe_sum(delivered, "Komisyon/Yurt Dışı Stok Destek Bedeli")
    discount = safe_sum(delivered, "İndirim")
    outbound_shipping = safe_sum(delivered, "Gönderi Kargo Bedeli")

    return_shipping = safe_sum(df, "İade Kargo Bedeli")
    penalty = safe_sum(df, "Ceza Bedeli")
    platform_fee = safe_sum(df, "Platform Hizmet Bedeli")
    net_amount = safe_sum(df, "Net Tutar")

    st.write("### Temmuz 2026 Özet")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Sipariş", f"{total_orders:,}")
    c2.metric("Teslim Edilen", f"{delivered_orders:,}")
    c3.metric("Satılan Adet", f"{int(units):,}")
    c4.metric("Teslim Edilen Ciro", money(revenue))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("İade", f"{returned_orders:,}")
    c6.metric("İptal", f"{cancelled_orders:,}")
    c7.metric("Komisyon", money(abs(commission)))
    c8.metric("Gönderi Kargo", money(abs(outbound_shipping)))

    st.write("### Kesintiler")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("İndirim", money(abs(discount)))
    k2.metric("İade Kargo", money(abs(return_shipping)))
    k3.metric("Platform Bedeli", money(abs(platform_fee)))
    k4.metric("Ceza", money(abs(penalty)))

    st.write("### Net Tutar")

    st.metric(
        "Excel Net Tutar Toplamı",
        money(net_amount)
    )
