from __future__ import annotations

import pandas as pd
import streamlit as st


PRODUCT_KEY_CANDIDATES = [
    "Stok Kodu",
    "Barkod",
    "Model Kodu",
    "Ürün Kodu",
    "Ürün Adı",
]
PRODUCT_NAME_CANDIDATES = ["Ürün Adı", "Ürün", "Ürün İsmi", "Product Name"]
STATUS_COL = "Sipariş Statüsü"
QTY_COL = "Ürün Adedi"
ORDER_AMOUNT_COL = "Sipariş Tutarı"
NET_AMOUNT_COL = "Net Tutar"

FEE_COLUMNS = {
    "Komisyon": "Komisyon/Yurt Dışı Stok Destek Bedeli",
    "Gönderi Kargo": "Gönderi Kargo Bedeli",
    "İade Kargo": "İade Kargo Bedeli",
    "İndirim": "İndirim",
    "Platform": "Platform Hizmet Bedeli",
    "Ceza": "Ceza Bedeli",
    "İade": "İade",
}


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((col for col in candidates if col in df.columns), None)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _money(value: float) -> str:
    return f"{value:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def _prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    key_col = _first_existing(df, PRODUCT_KEY_CANDIDATES)
    name_col = _first_existing(df, PRODUCT_NAME_CANDIDATES)

    if key_col is None:
        raise ValueError(
            "Ürün bazlı kârlılık için Stok Kodu, Barkod, Model Kodu, Ürün Kodu veya Ürün Adı sütunlarından biri gerekli."
        )
    if name_col is None:
        name_col = key_col

    work = df.copy()
    work["_product_key"] = work[key_col].fillna("Tanımsız").astype(str).str.strip()
    work["_product_name"] = work[name_col].fillna(work["_product_key"]).astype(str).str.strip()
    work.loc[work["_product_key"].eq(""), "_product_key"] = "Tanımsız"

    if STATUS_COL in work.columns:
        work["_status"] = work[STATUS_COL].fillna("").astype(str).str.strip()
    else:
        work["_status"] = ""

    for col in [QTY_COL, ORDER_AMOUNT_COL, NET_AMOUNT_COL, *FEE_COLUMNS.values()]:
        if col in work.columns:
            work[col] = _numeric(work[col])

    return work, key_col, name_col


def build_product_profitability(df: pd.DataFrame, costs: dict[str, float] | None = None) -> pd.DataFrame:
    costs = costs or {}
    work, _, _ = _prepare(df)

    delivered_mask = work["_status"].eq("Teslim Edildi") if STATUS_COL in work.columns else pd.Series(True, index=work.index)
    work["_delivered_units"] = 0.0
    work["_delivered_revenue"] = 0.0

    if QTY_COL in work.columns:
        work.loc[delivered_mask, "_delivered_units"] = work.loc[delivered_mask, QTY_COL]
    else:
        work.loc[delivered_mask, "_delivered_units"] = 1.0

    if ORDER_AMOUNT_COL in work.columns:
        work.loc[delivered_mask, "_delivered_revenue"] = work.loc[delivered_mask, ORDER_AMOUNT_COL]

    rows: list[dict] = []
    for product_key, group in work.groupby("_product_key", dropna=False):
        product_name = group["_product_name"].replace("", pd.NA).dropna()
        product_name_value = product_name.iloc[0] if not product_name.empty else str(product_key)

        delivered_units = float(group["_delivered_units"].sum())
        delivered_revenue = float(group["_delivered_revenue"].sum())
        financial_net = float(group[NET_AMOUNT_COL].sum()) if NET_AMOUNT_COL in group.columns else 0.0
        unit_cost = float(costs.get(str(product_key), 0.0) or 0.0)
        product_cost = delivered_units * unit_cost
        profit = financial_net - product_cost
        margin = (profit / delivered_revenue * 100.0) if delivered_revenue > 0 else 0.0

        fee_values = {}
        for label, col in FEE_COLUMNS.items():
            fee_values[label] = abs(float(group[col].sum())) if col in group.columns else 0.0

        if unit_cost <= 0:
            health = "⚪ Maliyet Eksik"
        elif profit < 0:
            health = "🔴 Zarar"
        elif margin < 10:
            health = "🟠 Düşük Marj"
        else:
            health = "🟢 Sağlıklı"

        rows.append({
            "Ürün Anahtarı": str(product_key),
            "Ürün": product_name_value,
            "Teslim Adet": delivered_units,
            "Teslim Ciro": delivered_revenue,
            "Trendyol Net": financial_net,
            "Birim Maliyet": unit_cost,
            "Ürün Maliyeti": product_cost,
            "Gerçek Kâr": profit,
            "Kâr Marjı %": margin,
            "Durum": health,
            **fee_values,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    rank = {"🔴 Zarar": 0, "🟠 Düşük Marj": 1, "⚪ Maliyet Eksik": 2, "🟢 Sağlıklı": 3}
    result["_rank"] = result["Durum"].map(rank).fillna(9)
    return result.sort_values(["_rank", "Gerçek Kâr"], ascending=[True, True]).drop(columns="_rank").reset_index(drop=True)


def render_product_profitability_v14(df: pd.DataFrame) -> None:
    st.markdown(
        '<div class="pg-card"><div class="pg-eyebrow">V1.4 • KÂRLILIK MERKEZİ</div>'
        '<h3>Hangi üründen gerçekten ne kadar kazanıyorsun?</h3>'
        '<p>ProfitGO, Trendyol Net Tutarını ürün maliyetiyle birleştirir. Komisyon, kargo, indirim, iade ve cezaların finansal etkisi Trendyol netinde korunur.</p></div>',
        unsafe_allow_html=True,
    )

    try:
        work, key_col, _ = _prepare(df)
    except ValueError as exc:
        st.warning(str(exc))
        return

    if "pg_product_costs_v14" not in st.session_state:
        st.session_state.pg_product_costs_v14 = {}

    products = (
        work[["_product_key", "_product_name"]]
        .drop_duplicates("_product_key")
        .sort_values("_product_name")
        .reset_index(drop=True)
    )
    products["Birim Maliyet (TL)"] = products["_product_key"].map(st.session_state.pg_product_costs_v14).fillna(0.0)
    cost_editor = products.rename(columns={"_product_key": "Ürün Anahtarı", "_product_name": "Ürün"})

    with st.expander("Ürün maliyetlerini gir / güncelle", expanded=True):
        st.caption(f"Eşleştirme alanı: {key_col}. Maliyetler bu demo oturumu boyunca saklanır.")
        edited = st.data_editor(
            cost_editor,
            width="stretch",
            hide_index=True,
            disabled=["Ürün Anahtarı", "Ürün"],
            column_config={
                "Birim Maliyet (TL)": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.2f"),
            },
            key="pg_cost_editor_v14",
        )
        if st.button("Maliyetleri uygula", type="primary", key="pg_apply_costs_v14"):
            st.session_state.pg_product_costs_v14 = {
                str(row["Ürün Anahtarı"]): float(row["Birim Maliyet (TL)"] or 0.0)
                for _, row in edited.iterrows()
            }
            st.success("Ürün maliyetleri kârlılık hesabına uygulandı.")
            st.rerun()

    result = build_product_profitability(df, st.session_state.pg_product_costs_v14)
    if result.empty:
        st.info("Ürün bazlı analiz oluşturulamadı.")
        return

    total_revenue = float(result["Teslim Ciro"].sum())
    total_net = float(result["Trendyol Net"].sum())
    total_cost = float(result["Ürün Maliyeti"].sum())
    total_profit = float(result["Gerçek Kâr"].sum())
    total_margin = (total_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Teslim Edilen Ciro", _money(total_revenue))
    c2.metric("Trendyol Net", _money(total_net))
    c3.metric("Ürün Maliyeti", _money(total_cost))
    c4.metric("Gerçek Kâr", _money(total_profit), f"%{total_margin:.1f} marj")

    losing = int(result["Durum"].eq("🔴 Zarar").sum())
    low_margin = int(result["Durum"].eq("🟠 Düşük Marj").sum())
    missing_cost = int(result["Durum"].eq("⚪ Maliyet Eksik").sum())

    if losing:
        st.error(f"{losing} ürün zarar ediyor. Öncelikli fiyat/maliyet kontrolü öneriliyor.")
    elif low_margin:
        st.warning(f"{low_margin} ürünün kâr marjı %10'un altında.")
    elif missing_cost:
        st.info(f"{missing_cost} ürün için maliyet girildiğinde gerçek kâr hesabı tamamlanacak.")
    else:
        st.success("Maliyeti tanımlı ürünlerde zarar veya düşük marj alarmı yok.")

    display = result.copy()
    money_cols = [
        "Teslim Ciro", "Trendyol Net", "Birim Maliyet", "Ürün Maliyeti", "Gerçek Kâr",
        "Komisyon", "Gönderi Kargo", "İade Kargo", "İndirim", "Platform", "Ceza", "İade",
    ]
    for col in money_cols:
        if col in display.columns:
            display[col] = display[col].map(_money)
    display["Teslim Adet"] = display["Teslim Adet"].round(0).astype(int)
    display["Kâr Marjı %"] = display["Kâr Marjı %"].map(lambda x: f"%{x:.1f}")

    st.write("### Ürün Kârlılık Tablosu")
    st.dataframe(display, width="stretch", hide_index=True)

    st.caption(
        "V1.4 hesap mantığı: ürün finansal neti = Trendyol raporundaki Net Tutar toplamı; gerçek kâr = ürün finansal neti − teslim edilen adet × birim maliyet."
    )
