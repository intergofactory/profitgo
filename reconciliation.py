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


def render_reconciliation():
    st.divider()
    st.subheader("🧮 ProfitGO Mutabakat Motoru")

    if "trendyol_orders" not in st.session_state:
        st.info(
            "Mutabakat için önce Trendyol Sipariş Kayıtları "
            "Excel dosyasını yükleyin."
        )
        return

    df = st.session_state["trendyol_orders"].copy()

    columns = [
        "Sipariş Tutarı",
        "Komisyon/Yurt Dışı Stok Destek Bedeli",
        "İndirim",
        "Gönderi Kargo Bedeli",
        "İade Kargo Bedeli",
        "Ceza Bedeli",
        "İptal",
        "İade",
        "Diğer",
        "Yurtdışı Operasyon İade Bedeli",
        "Uluslararası Hizmet Bedeli",
        "Platform Hizmet Bedeli",
    ]

    values = {}

    for column in columns:
        values[column] = safe_sum(df, column)

    profitgo_net = sum(values.values())

    trendyol_net = safe_sum(
        df,
        "Net Tutar"
    )

    difference = trendyol_net - profitgo_net

    st.write("### Finansal Kalemler")

    rows = []

    for column, value in values.items():
        rows.append(
            {
                "Kalem": column,
                "Tutar (TL)": value,
            }
        )

    rows.append(
        {
            "Kalem": "ProfitGO Hesaplanan Net",
            "Tutar (TL)": profitgo_net,
        }
    )

    rows.append(
        {
            "Kalem": "Trendyol Net Tutar",
            "Tutar (TL)": trendyol_net,
        }
    )

    rows.append(
        {
            "Kalem": "Fark",
            "Tutar (TL)": difference,
        }
    )

    reconciliation_df = pd.DataFrame(rows)

    st.dataframe(
        reconciliation_df,
        width="stretch",
        hide_index=True,
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "ProfitGO Hesaplanan Net",
        money(profitgo_net)
    )

    c2.metric(
        "Trendyol Net Tutar",
        money(trendyol_net)
    )

    c3.metric(
        "Açıklanamayan Fark",
        money(difference)
    )

    if abs(difference) < 1:
        st.success(
            "ProfitGO hesabı ile Trendyol Net Tutarı "
            "kuruş seviyesinde uyumlu."
        )
    else:
        st.warning(
            "ProfitGO hesabı ile Trendyol Net Tutarı arasında "
            f"{money(difference)} fark var. "
            "Bu fark detay incelemeye alınmalı."
        )
