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
    st.divider()
    st.write("### 🔎 ProfitGO Kontrol Tablosu")

    kontrol = {
        "Teslim Edilen Ciro": revenue,
        "Komisyon": abs(commission),
        "Gönderi Kargo": abs(outbound_shipping),
        "İndirim": abs(discount),
        "İade Kargo": abs(return_shipping),
        "Platform Bedeli": abs(platform_fee),
        "Ceza": abs(penalty),
        "Excel Net Tutar": net_amount,
    }

    kontrol_df = pd.DataFrame(
        {
            "Kalem": kontrol.keys(),
            "Tutar (TL)": kontrol.values(),
        }
    )

    st.dataframe(
        kontrol_df,
        width="stretch",
        hide_index=True,
    )
    # ==================================================
    # ProfitGO - Mükerrer / Hatalı Kesinti Avcısı
    # ==================================================

    st.divider()
    st.subheader("🚨 ProfitGO Kesinti Avcısı")

    order_col = "Sipariş No"

    fee_columns = [
        "Komisyon/Yurt Dışı Stok Destek Bedeli",
        "Gönderi Kargo Bedeli",
        "İade Kargo Bedeli",
        "Ceza Bedeli",
        "Platform Hizmet Bedeli",
    ]

    existing_fee_columns = [
        col for col in fee_columns if col in df.columns
    ]

    if order_col in df.columns and existing_fee_columns:

        duplicate_check = (
            df.groupby(order_col)[existing_fee_columns]
            .agg(["count", "sum"])
        )

        suspicious_orders = []

        for order_no, group in df.groupby(order_col):

            issues = []

            for col in existing_fee_columns:
                non_zero = group[col].fillna(0)
                non_zero = non_zero[non_zero != 0]

                if len(non_zero) > 1:
                    issues.append(
                        f"{col}: {len(non_zero)} ayrı kesinti"
                    )

            if issues:
                suspicious_orders.append({
                    "Sipariş No": order_no,
                    "Şüpheli Durum": " | ".join(issues)
                })

        if suspicious_orders:
            suspicious_df = pd.DataFrame(suspicious_orders)

            st.warning(
                f"{len(suspicious_df)} siparişte birden fazla kesinti hareketi bulundu."
            )

            st.dataframe(
                suspicious_df,
                width="stretch"
            )

        else:
            st.success(
                "İlk kontrolde mükerrer kesinti şüphesi bulunmadı."
            )

    else:
        st.info(
            "Kesinti avcısı için gerekli sipariş/kesinti sütunları bulunamadı."
        )
    # ==================================================
    # ProfitGO - Seviye 2 Akıllı Denetim
    # İptal / İade Sonrası Kesinti Kontrolü
    # ==================================================

    st.divider()
    st.subheader("🧠 ProfitGO Akıllı Denetim")

    audit_rows = []

    audit_columns = [
        "Komisyon/Yurt Dışı Stok Destek Bedeli",
        "Gönderi Kargo Bedeli",
        "İade Kargo Bedeli",
        "Ceza Bedeli",
        "Platform Hizmet Bedeli",
    ]

    for _, row in df.iterrows():

        status = str(row.get("Sipariş Statüsü", "")).strip()
        order_no = row.get("Sipariş No", "")

        commission_value = float(
            pd.to_numeric(
                row.get(
                    "Komisyon/Yurt Dışı Stok Destek Bedeli",
                    0
                ),
                errors="coerce"
            )
            if pd.notna(
                pd.to_numeric(
                    row.get(
                        "Komisyon/Yurt Dışı Stok Destek Bedeli",
                        0
                    ),
                    errors="coerce"
                )
            )
            else 0
        )

        outbound_value = float(
            pd.to_numeric(
                row.get("Gönderi Kargo Bedeli", 0),
                errors="coerce"
            )
            if pd.notna(
                pd.to_numeric(
                    row.get("Gönderi Kargo Bedeli", 0),
                    errors="coerce"
                )
            )
            else 0
        )

        return_value = float(
            pd.to_numeric(
                row.get("İade Kargo Bedeli", 0),
                errors="coerce"
            )
            if pd.notna(
                pd.to_numeric(
                    row.get("İade Kargo Bedeli", 0),
                    errors="coerce"
                )
            )
            else 0
        )

        platform_value = float(
            pd.to_numeric(
                row.get("Platform Hizmet Bedeli", 0),
                errors="coerce"
            )
            if pd.notna(
                pd.to_numeric(
                    row.get("Platform Hizmet Bedeli", 0),
                    errors="coerce"
                )
            )
            else 0
        )

        penalty_value = float(
            pd.to_numeric(
                row.get("Ceza Bedeli", 0),
                errors="coerce"
            )
            if pd.notna(
                pd.to_numeric(
                    row.get("Ceza Bedeli", 0),
                    errors="coerce"
                )
            )
            else 0
        )

        issues = []
        suspicious_amount = 0.0

        if status == "İptal Edildi":

            if commission_value != 0:
                issues.append("İptal sonrası komisyon")
                suspicious_amount += abs(commission_value)

            if outbound_value != 0:
                issues.append("İptal sonrası gönderi kargosu")
                suspicious_amount += abs(outbound_value)

            if platform_value != 0:
                issues.append("İptal sonrası platform bedeli")
                suspicious_amount += abs(platform_value)

            if penalty_value != 0:
                issues.append("İptal sonrası ceza")
                suspicious_amount += abs(penalty_value)

        elif status == "İade Edildi":

            if (
                commission_value != 0
                or outbound_value != 0
                or return_value != 0
                or platform_value != 0
            ):
                issues.append(
                    "İade siparişi - finansal hareket incele"
                )

        if issues:
            audit_rows.append(
                {
                    "Sipariş No": order_no,
                    "Statü": status,
                    "Şüpheli Durum": " | ".join(issues),
                    "Şüpheli Tutar (TL)": suspicious_amount,
                }
            )

    if audit_rows:

        audit_df = pd.DataFrame(audit_rows)

        cancelled_audit = audit_df[
            audit_df["Statü"] == "İptal Edildi"
        ]

        total_suspicious = cancelled_audit[
            "Şüpheli Tutar (TL)"
        ].sum()

        a1, a2 = st.columns(2)

        a1.metric(
            "İncelenecek Sipariş",
            f"{len(audit_df):,}"
        )

        a2.metric(
            "İptal Sonrası Şüpheli Tutar",
            money(total_suspicious)
        )

        st.dataframe(
            audit_df,
            width="stretch",
            hide_index=True
        )

        st.warning(
            "Bu kayıtlar otomatik olarak hatalı kabul edilmez. "
            "ProfitGO bunları detay doğrulaması için işaretler."
        )

    else:
        st.success(
            "İptal/iade sonrası incelenmesi gereken "
            "finansal hareket bulunmadı."
        )
