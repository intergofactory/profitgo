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
    # ==================================================
    # ProfitGO - İade Maliyeti Analizi
    # ==================================================

    st.divider()
    st.subheader("↩️ ProfitGO İade Maliyeti Analizi")

    returned_df = df[
        df["Sipariş Statüsü"]
        .astype(str)
        .str.strip()
        .eq("İade Edildi")
    ].copy()

    if not returned_df.empty:

        return_revenue = safe_sum(
            returned_df,
            "Sipariş Tutarı"
        )

        return_commission = safe_sum(
            returned_df,
            "Komisyon/Yurt Dışı Stok Destek Bedeli"
        )

        return_outbound_shipping = safe_sum(
            returned_df,
            "Gönderi Kargo Bedeli"
        )

        return_return_shipping = safe_sum(
            returned_df,
            "İade Kargo Bedeli"
        )

        return_discount = safe_sum(
            returned_df,
            "İndirim"
        )

        return_platform = safe_sum(
            returned_df,
            "Platform Hizmet Bedeli"
        )

        return_penalty = safe_sum(
            returned_df,
            "Ceza Bedeli"
        )

        return_net = safe_sum(
            returned_df,
            "Net Tutar"
        )

        r1, r2, r3, r4 = st.columns(4)

        r1.metric(
            "İade Siparişi",
            f"{len(returned_df):,}"
        )

        r2.metric(
            "İade Sipariş Tutarı",
            money(return_revenue)
        )

        r3.metric(
            "İade Kargo Maliyeti",
            money(abs(return_return_shipping))
        )

        r4.metric(
            "İadelerin Net Finansal Etkisi",
            money(return_net)
        )

        st.write("### İade Finansal Kalemleri")

        return_rows = [
            {
                "Kalem": "Sipariş Tutarı",
                "Tutar (TL)": return_revenue,
            },
            {
                "Kalem": "Komisyon",
                "Tutar (TL)": return_commission,
            },
            {
                "Kalem": "Gönderi Kargo",
                "Tutar (TL)": return_outbound_shipping,
            },
            {
                "Kalem": "İade Kargo",
                "Tutar (TL)": return_return_shipping,
            },
            {
                "Kalem": "İndirim",
                "Tutar (TL)": return_discount,
            },
            {
                "Kalem": "Platform Bedeli",
                "Tutar (TL)": return_platform,
            },
            {
                "Kalem": "Ceza",
                "Tutar (TL)": return_penalty,
            },
            {
                "Kalem": "Net Tutar",
                "Tutar (TL)": return_net,
            },
        ]

        st.dataframe(
            pd.DataFrame(return_rows),
            width="stretch",
            hide_index=True
        )

        returned_df["_return_cost_score"] = (
            returned_df.get(
                "Gönderi Kargo Bedeli",
                0
            ).fillna(0).abs()
            +
            returned_df.get(
                "İade Kargo Bedeli",
                0
            ).fillna(0).abs()
            +
            returned_df.get(
                "Komisyon/Yurt Dışı Stok Destek Bedeli",
                0
            ).fillna(0).abs()
            +
            returned_df.get(
                "Platform Hizmet Bedeli",
                0
            ).fillna(0).abs()
        )

        expensive_returns = returned_df.sort_values(
            "_return_cost_score",
            ascending=False
        ).head(20)

        st.write("### En Maliyetli 20 İade")

        show_columns = [
            col for col in [
                "Sipariş No",
                "Sipariş Tutarı",
                "Komisyon/Yurt Dışı Stok Destek Bedeli",
                "Gönderi Kargo Bedeli",
                "İade Kargo Bedeli",
                "Platform Hizmet Bedeli",
                "Net Tutar",
                "_return_cost_score",
            ]
            if col in expensive_returns.columns
        ]

        st.dataframe(
            expensive_returns[show_columns],
            width="stretch",
            hide_index=True
        )

    else:
        st.success(
            "İade edilmiş sipariş bulunmadı."
        )
    # ==================================================
    # ProfitGO - Ceza Kaynağı Analizi
    # ==================================================

    st.divider()
    st.subheader("⚠️ ProfitGO Ceza Kaynağı Analizi")

    penalty_df = df.copy()

    if "Ceza Bedeli" in penalty_df.columns:
        penalty_df["Ceza Bedeli"] = pd.to_numeric(
            penalty_df["Ceza Bedeli"],
            errors="coerce"
        ).fillna(0)

        penalty_df = penalty_df[
            penalty_df["Ceza Bedeli"] != 0
        ].copy()

        if not penalty_df.empty:

            total_penalty = abs(
                penalty_df["Ceza Bedeli"].sum()
            )

            p1, p2 = st.columns(2)

            p1.metric(
                "Ceza Kesilen Sipariş",
                f"{len(penalty_df):,}"
            )

            p2.metric(
                "Toplam Ceza",
                money(total_penalty)
            )

            show_columns = [
                col for col in [
                    "Sipariş No",
                    "Sipariş Tarihi",
                    "Sipariş Statüsü",
                    "Sipariş Tutarı",
                    "Ceza Bedeli",
                    "Net Tutar",
                ]
                if col in penalty_df.columns
            ]

            penalty_view = penalty_df[
                show_columns
            ].sort_values(
                "Ceza Bedeli"
            )

            st.dataframe(
                penalty_view,
                width="stretch",
                hide_index=True
            )

        else:
            st.success(
                "Ceza bedeli bulunan sipariş yok."
            )

    else:
        st.info(
            "Excel dosyasında Ceza Bedeli sütunu bulunamadı."
        )
    # =========================================================
    # ProfitGO Ceza Denetçisi
    # =========================================================

    st.divider()
    st.write("### 🚨 ProfitGO Ceza Denetçisi")

    if "Ceza Bedeli" in df.columns:

        penalty_df = df.copy()
        penalty_values = pd.to_numeric(
            penalty_df["Ceza Bedeli"],
            errors="coerce"
        ).fillna(0)

        penalty_df = penalty_df[penalty_values != 0].copy()

        if not penalty_df.empty:

            def penalty_status(row):
                order_status = str(row.get("Sipariş Statüsü", "")).replace("İ", "i").replace("I", "ı").strip().lower()
                penalty_amount = abs(pd.to_numeric(row.get("Ceza Bedeli", 0), errors="coerce") or 0)
                return_shipping = abs(pd.to_numeric(row.get("İade Kargo Bedeli", 0), errors="coerce") or 0)
                outbound_shipping = abs(pd.to_numeric(row.get("Gönderi Kargo Bedeli", 0), errors="coerce") or 0)
                net_amount = pd.to_numeric(row.get("Net Tutar", 0), errors="coerce") or 0
                if "iade" in order_status:
                    return "🟡 İncelenmeli – İade"

                if "iptal" in order_status:
                    return "🟡 İncelenmeli – İptal"
                order_amount = abs(pd.to_numeric(row.get("Sipariş Tutarı", 0), errors="coerce") or 0)
                refund_amount = abs(pd.to_numeric(row.get("İade", 0), errors="coerce") or 0)
                if "yeni sipariş" in order_status:
                    refund_ratio = (
                        refund_amount / order_amount
                        if order_amount > 0
                        else 0
                    )

                    if refund_amount > 0 and refund_ratio > 0:
                        return "🟠 Güçlü Şüphe – Yeni Sipariş / Kısmi İade"

                    if penalty_amount >= 500 and return_shipping == 0 and net_amount > 0:
                        return "🔴 MUHTEMEL HATALI – Yeni Sipariş"

                    return "🟠 Güçlü Şüphe – Yeni Sipariş"
                order_amount = abs(pd.to_numeric(row.get("Sipariş Tutarı", 0), errors="coerce") or 0)
                refund_amount = abs(pd.to_numeric(row.get("İade", 0), errors="coerce") or 0)
                if "teslim" in order_status:
                    refund_ratio = (
                        refund_amount / order_amount
                        if order_amount > 0
                        else 0
                    )

                    if refund_amount > 0 and refund_ratio >= 0.25:
                        return "🟡 İncelenmeli – Kısmi İade"

                    if penalty_amount >= 500 and return_shipping == 0:
                        return "🔴 MUHTEMEL HATALI – Teslim Edilmiş"

                return "🟠 Güçlü Şüphe – Teslim Edilmiş"
                return "🟡 İncelenmeli"
            penalty_df["ProfitGO Denetim"] = penalty_df.apply(
                penalty_status,
                axis=1
            )
            penalty_df["ProfitGO Açıklama"] = penalty_df["ProfitGO Denetim"].map({
                "🔴 MUHTEMEL HATALI – Yeni Sipariş":
                    "Sipariş hâlâ Yeni Sipariş statüsünde olmasına rağmen yüksek tutarlı ceza kesilmiş. Ceza gerekçesi öncelikli olarak doğrulanmalı.",
               
                "🟠 Güçlü Şüphe – Yeni Sipariş / Kısmi İade":
                    "Siparişte kısmi iade hareketi bulunuyor. Ceza bu iade ile ilişkili olabilir; ceza gerekçesi doğrulanmalı.",

                "🟠 Güçlü Şüphe – Yeni Sipariş":
                    "Sipariş Yeni Sipariş statüsünde olmasına rağmen ceza kesilmiş. Ceza gerekçesi kontrol edilmeli.",

                "🔴 MUHTEMEL HATALI – Teslim Edilmiş":
                    "Sipariş teslim edilmiş olmasına rağmen yüksek tutarlı ceza kesilmiş. Ceza gerekçesi öncelikli olarak doğrulanmalı.",

                "🟠 Güçlü Şüphe – Teslim Edilmiş":
                    "Sipariş teslim edilmiş olmasına rağmen ceza kesilmiş. Ceza gerekçesi kontrol edilmeli.",

                "🟡 İncelenmeli – İade":
                    "Ceza iade süreciyle ilişkili görünüyor. Hata olarak kabul edilmeden önce iade hareketleriyle birlikte kontrol edilmeli.",

                "🟡 İncelenmeli – İptal":
                    "Ceza iptal süreciyle ilişkili görünüyor. Hata olarak kabul edilmeden önce sipariş hareketleriyle birlikte kontrol edilmeli.",

                "🟡 İncelenmeli":
                    "Sipariş statüsünden cezanın nedeni kesin olarak belirlenemedi."
            }).fillna("Manuel kontrol gerekli.")
            suspicious_mask = penalty_df["ProfitGO Denetim"].str.contains(
                "MUHTEMEL HATALI|Güçlü Şüphe",
                na=False,
                regex=True
            )

            suspicious_df = penalty_df[suspicious_mask].copy()
            st.write("### 🔍 Yalnızca Şüpheli Ceza Kayıtları")
            st.dataframe(suspicious_df, width="stretch", hide_index=True)

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Ceza Kesilen Sipariş",
                f"{len(penalty_df):,}"
            )

            c2.metric(
                "Şüpheli Ceza Kaydı",
                f"{len(suspicious_df):,}"
            )

            suspicious_total = pd.to_numeric(
                suspicious_df["Ceza Bedeli"],
                errors="coerce"
            ).fillna(0).abs().sum()

            c3.metric(
                "Şüpheli Ceza Tutarı",
                money(suspicious_total)
            )

            st.write("#### Ceza Denetim Sonuçları")

            show_columns = [
                col for col in [
                    "Sipariş No",
                    "Sipariş Tarihi",
                    "Sipariş Statüsü",
                    "Sipariş Tutarı",
               	    "Komisyon/Yurt Dışı Stok Destek Bedeli",
               	    "İndirim",
               	    "Gönderi Kargo Bedeli",
               	    "İade Kargo Bedeli",
               	    "Platform Hizmet Bedeli",
                    "Ceza Bedeli",
                    "Net Tutar",
                    "ProfitGO Denetim",
           	    "ProfitGO Açıklama",
                ]
                if col in penalty_df.columns
            ]

            st.dataframe(
                penalty_df[show_columns],
                width="stretch",
                hide_index=True
            )

            if not suspicious_df.empty:
                st.error(
                    f"ProfitGO {len(suspicious_df)} adet şüpheli ceza kaydı "
                    f"tespit etti. Toplam şüpheli tutar: "
                    f"{money(suspicious_total)}"
                )
            else:
                st.success(
                    "Sipariş statüsüne göre şüpheli ceza kaydı bulunamadı."
                )

        else:
            st.success("Ceza kesilmiş sipariş bulunamadı.")

    else:
        st.warning("Excel dosyasında 'Ceza Bedeli' sütunu bulunamadı.")
