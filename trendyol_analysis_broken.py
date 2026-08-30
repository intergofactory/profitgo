import streamlit as st
import pandas as pd


def money(value):
    return f"{value:,.2f} TL"


def safe_sum(df, column_name):
    if column_name not in df.columns:
        return 0.0

    series = pd.to_numeric(
        df[column_name],
        errors="coerce"
    ).fillna(0)

    return float(series.sum())


def render_trendyol_analysis():
    st.divider()
    st.subheader("📊 Trendyol Finansal Analiz")

    if "trendyol_orders" not in st.session_state:
        st.info(
            "Analiz için önce Trendyol Sipariş Kayıtları "
            "Excel dosyasını yükleyin."
        )
        return

    df = st.session_state["trendyol_orders"].copy()

    if df.empty:
        st.warning("Yüklenen Excel dosyasında veri bulunamadı.")
        return

    total_rows = len(df)

    delivered_df = df.copy()

    if "Sipariş Statüsü" in df.columns:
        delivered_df = df[
            df["Sipariş Statüsü"]
            .astype(str)
            .str.strip()
            .eq("Teslim Edildi")
        ].copy()

    total_revenue = safe_sum(
        delivered_df,
        "Sipariş Tutarı"
    )

    total_units = safe_sum(
        delivered_df,
        "Ürün Adedi"
    )

    commission = safe_sum(
        delivered_df,
        "Komisyon/Yurt Dışı Stok Destek Bedeli"
    )

    discount = safe_sum(
        delivered_df,
        "İndirim"
    )

    outbound_shipping = safe_sum(
        delivered_df,
        "Gönderi Kargo Bedeli"
    )

    return_shipping = safe_sum(
        df,
        "İade Kargo Bedeli"
    )

    penalty = safe_sum(
        df,
        "Ceza Bedeli"
    )

    platform_fee = safe_sum(
        df,
        "Platform Hizmet Bedeli"
    )

    net_amount = safe_sum(
        df,
        "Net Tutar"
    )

    cancelled_count = 0
    returned_count = 0

    if "Sipariş Statüsü" in df.columns:
        statuses = (
            df["Sipariş Statüsü"]
            .astype(str)
            .str.strip()
        )

        cancelled_count = int(
            statuses.eq("İptal Edildi").sum()
        )

        returned_count = int(
            statuses.eq("İade Edildi").sum()
        )

    st.write("### Temmuz 2026 Özet")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Toplam Sipariş Kaydı",
