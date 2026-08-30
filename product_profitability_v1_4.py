from __future__ import annotations

import re
import pandas as pd
import streamlit as st

STATUS_COL = "Sipariş Statüsü"
ORDER_COL = "Sipariş No"
QTY_COL = "Ürün Adedi"
GROSS_COL = "Sipariş Tutarı"
NET_COL = "Net Tutar"
FEE_COLS = {
    "Komisyon": "Komisyon/Yurt Dışı Stok Destek Bedeli",
    "İndirim": "İndirim",
    "Gönderi Kargo": "Gönderi Kargo Bedeli",
    "İade Kargo": "İade Kargo Bedeli",
    "Platform": "Platform Hizmet Bedeli",
    "Ceza": "Ceza Bedeli",
}


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def money(v):
    return f"{v:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def _model_from_name(name: str) -> str:
    text = str(name or "")
    match = re.search(r"([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s*,\s*one size", text, flags=re.I)
    if match:
        return match.group(1).upper()
    return ""


def build_order_product_map(invoice_df: pd.DataFrame):
    required = {ORDER_COL, "Ürün Adı"}
    if not required.issubset(invoice_df.columns):
        return {}, {}, 0
    inv = invoice_df.copy()
    if "İşlem Tipi" in inv.columns:
        sale_mask = inv["İşlem Tipi"].fillna("").astype(str).str.strip().str.lower().isin(["satış", "yenilenmiş satış"])
        inv = inv[sale_mask].copy()
    inv["_order"] = inv[ORDER_COL].astype(str).str.replace(r"\.0$", "", regex=True)
    inv["_model"] = inv["Ürün Adı"].map(_model_from_name)
    inv = inv[inv["_model"].ne("")]
    model_names = inv.groupby("_model")["Ürün Adı"].first().to_dict()
    grouped = inv.groupby("_order")["_model"].agg(lambda x: sorted(set(x)))
    mapping = {order: models[0] for order, models in grouped.items() if len(models) == 1}
    multi_count = int((grouped.map(len) > 1).sum())
    return mapping, model_names, multi_count


def build_product_profitability(order_df: pd.DataFrame, invoice_df: pd.DataFrame, costs=None):
    costs = costs or {}
    if ORDER_COL not in order_df.columns:
        raise ValueError("Sipariş Kayıtları dosyasında Sipariş No sütunu bulunamadı.")
    mapping, model_names, multi_count = build_order_product_map(invoice_df)
    if not mapping:
        raise ValueError("Satıcı Fatura dosyalarından ürün-model eşleştirmesi oluşturulamadı.")

    work = order_df.copy()
    work["_order"] = work[ORDER_COL].astype(str).str.replace(r"\.0$", "", regex=True)
    work["Model Kodu"] = work["_order"].map(mapping)
    mapped = work[work["Model Kodu"].notna()].copy()
    if mapped.empty:
        raise ValueError("Siparişler ile Satıcı Fatura kayıtları eşleşmedi.")

    for col in [QTY_COL, GROSS_COL, NET_COL, *FEE_COLS.values()]:
        if col in mapped.columns:
            mapped[col] = _num(mapped[col])
    delivered = mapped[mapped[STATUS_COL].astype(str).str.strip().eq("Teslim Edildi")].copy() if STATUS_COL in mapped.columns else mapped

    rows = []
    for model, group in delivered.groupby("Model Kodu"):
        qty = float(group[QTY_COL].sum()) if QTY_COL in group else float(len(group))
        gross = float(group[GROSS_COL].sum()) if GROSS_COL in group else 0.0
        net = float(group[NET_COL].sum()) if NET_COL in group else 0.0
        cost = float(costs.get(str(model), 0.0) or 0.0)
        cogs = qty * cost
        profit = net - cogs
        margin = profit / gross * 100 if gross else 0.0
        status = "⚪ Maliyet Eksik" if cost <= 0 else ("🔴 Zarar" if profit < 0 else ("🟠 Düşük Marj" if margin < 10 else "🟢 Sağlıklı"))
        row = {"Model Kodu": model, "Ürün": model_names.get(model, model), "Sipariş": len(group), "Teslim Adet": qty,
               "Teslim Ciro": gross, "Trendyol Net": net, "Birim Maliyet": cost, "Ürün Maliyeti": cogs,
               "Gerçek Kâr": profit, "Kâr Marjı %": margin, "Durum": status}
        for label, col in FEE_COLS.items():
            row[label] = abs(float(group[col].sum())) if col in group else 0.0
        rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty:
        rank = {"🔴 Zarar": 0, "🟠 Düşük Marj": 1, "⚪ Maliyet Eksik": 2, "🟢 Sağlıklı": 3}
        result["_rank"] = result["Durum"].map(rank).fillna(9)
        result = result.sort_values(["_rank", "Gerçek Kâr"]).drop(columns="_rank").reset_index(drop=True)
    stats = {"mapped_orders": mapped["_order"].nunique(), "total_orders": work["_order"].nunique(), "multi_product_orders": multi_count,
             "unmapped_orders": work.loc[work["Model Kodu"].isna(), "_order"].nunique()}
    return result, stats


def render_product_profitability_v14(order_df: pd.DataFrame, invoice_df: pd.DataFrame) -> None:
    st.markdown('<div class="pg-card"><div class="pg-eyebrow">V1.4 • KÂRLILIK MERKEZİ</div><h3>Hangi üründen gerçekten ne kadar kazanıyorsun?</h3><p>Sipariş Kayıtları finansal hareketleri, Satıcı Fatura dosyalarındaki ürün/model bilgisiyle eşleştirilir. Böylece sipariş raporunda ürün sütunu olmasa bile ürün bazlı kârlılık hesaplanır.</p></div>', unsafe_allow_html=True)
    if "pg_product_costs_v14" not in st.session_state:
        st.session_state.pg_product_costs_v14 = {}
    try:
        preview, stats = build_product_profitability(order_df, invoice_df, st.session_state.pg_product_costs_v14)
    except ValueError as exc:
        st.warning(str(exc)); return
    if preview.empty:
        st.info("Kârlılık tablosu oluşturulamadı."); return

    st.caption(f"{stats['mapped_orders']:,} sipariş ürün modeliyle eşleşti • {stats['multi_product_orders']} çok ürünlü sipariş güvenli hesap için ürün tablosundan hariç tutuldu • {stats['unmapped_orders']} sipariş eşleşmedi".replace(",", "."))
    cost_table = preview[["Model Kodu", "Ürün"]].drop_duplicates().copy()
    cost_table["Birim Maliyet (TL)"] = cost_table["Model Kodu"].map(st.session_state.pg_product_costs_v14).fillna(0.0)
    with st.expander("Ürün maliyetlerini gir / güncelle", expanded=True):
        edited = st.data_editor(cost_table, width="stretch", hide_index=True, disabled=["Model Kodu", "Ürün"],
            column_config={"Birim Maliyet (TL)": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.2f")}, key="pg_cost_editor_v14")
        if st.button("Maliyetleri uygula", type="primary", key="pg_apply_costs_v14"):
            st.session_state.pg_product_costs_v14 = {str(r["Model Kodu"]): float(r["Birim Maliyet (TL)"] or 0) for _, r in edited.iterrows()}
            st.rerun()

    result, stats = build_product_profitability(order_df, invoice_df, st.session_state.pg_product_costs_v14)
    total_gross = float(result["Teslim Ciro"].sum()); total_net = float(result["Trendyol Net"].sum()); total_cogs = float(result["Ürün Maliyeti"].sum()); total_profit = float(result["Gerçek Kâr"].sum())
    margin = total_profit / total_gross * 100 if total_gross else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Eşleşen Ciro", money(total_gross)); c2.metric("Trendyol Net", money(total_net)); c3.metric("Ürün Maliyeti", money(total_cogs)); c4.metric("Gerçek Kâr", money(total_profit), f"%{margin:.1f} marj")

    losing = int(result["Durum"].eq("🔴 Zarar").sum()); low = int(result["Durum"].eq("🟠 Düşük Marj").sum()); missing = int(result["Durum"].eq("⚪ Maliyet Eksik").sum())
    if losing: st.error(f"{losing} ürün modeli zarar ediyor.")
    elif low: st.warning(f"{low} ürün modelinin marjı %10'un altında.")
    elif missing: st.info(f"{missing} ürün modeli için maliyet girilmesi gerekiyor.")
    else: st.success("Maliyeti tanımlı ürünlerde kârlılık alarmı yok.")

    display = result.copy()
    for col in ["Teslim Ciro","Trendyol Net","Birim Maliyet","Ürün Maliyeti","Gerçek Kâr",*FEE_COLS.keys()]:
        if col in display: display[col] = display[col].map(money)
    display["Teslim Adet"] = display["Teslim Adet"].round(0).astype(int)
    display["Kâr Marjı %"] = display["Kâr Marjı %"].map(lambda x: f"%{x:.1f}")
    st.write("### Ürün Kârlılık Tablosu")
    st.dataframe(display, width="stretch", hide_index=True)
    st.caption("Hesap: Gerçek Kâr = Trendyol Net Tutar − (Teslim Edilen Adet × Birim Maliyet). Çok ürünlü siparişler yanlış maliyet dağıtımı yapmamak için bu sürümde hariç tutulur.")
