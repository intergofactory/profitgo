from __future__ import annotations

import io
import json
import os
import hashlib
from datetime import datetime

import pandas as pd
import streamlit as st


def _numeric_sum(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _status_series(df: pd.DataFrame) -> pd.Series:
    if "Sipariş Statüsü" not in df.columns:
        return pd.Series([""] * len(df), index=df.index)
    return df["Sipariş Statüsü"].astype(str).str.strip()


def build_summary(df: pd.DataFrame, filename: str = "Trendyol Raporu") -> dict:
    status = _status_series(df)
    delivered = df[status.eq("Teslim Edildi")]
    penalty_values = pd.to_numeric(df.get("Ceza Bedeli", pd.Series([0] * len(df))), errors="coerce").fillna(0)
    penalty_mask = penalty_values.ne(0)

    suspicious_count = 0
    suspicious_amount = 0.0
    if penalty_mask.any():
        p = df.loc[penalty_mask].copy()
        p_penalty = pd.to_numeric(p.get("Ceza Bedeli", 0), errors="coerce").fillna(0).abs()
        p_status = (
            p.get("Sipariş Statüsü", pd.Series([""] * len(p), index=p.index))
            .astype(str)
            .str.replace("İ", "i", regex=False)
            .str.replace("I", "ı", regex=False)
            .str.lower()
        )
        refund = pd.to_numeric(p.get("İade", 0), errors="coerce").fillna(0).abs()
        order_amount = pd.to_numeric(p.get("Sipariş Tutarı", 0), errors="coerce").fillna(0).abs()
        refund_ratio = refund.div(order_amount.where(order_amount.ne(0), 1))
        new_partial = p_status.str.contains("yeni sipariş", na=False) & refund.gt(0)
        new_risk = p_status.str.contains("yeni sipariş", na=False) & (~new_partial) & p_penalty.ge(500)
        delivered_risk = p_status.str.contains("teslim", na=False) & refund_ratio.lt(0.25)
        suspicious = new_partial | new_risk | delivered_risk
        suspicious_count = int(suspicious.sum())
        suspicious_amount = float(p_penalty[suspicious].sum())

    commission = abs(_numeric_sum(df, "Komisyon/Yurt Dışı Stok Destek Bedeli"))
    shipping = abs(_numeric_sum(df, "Gönderi Kargo Bedeli"))
    return_shipping = abs(_numeric_sum(df, "İade Kargo Bedeli"))
    platform_fee = abs(_numeric_sum(df, "Platform Hizmet Bedeli"))
    penalty = abs(_numeric_sum(df, "Ceza Bedeli"))
    returns = abs(_numeric_sum(df, "İade"))
    delivered_revenue = _numeric_sum(delivered, "Sipariş Tutarı")
    total_deductions = commission + shipping + return_shipping + platform_fee + penalty
    deduction_rate = (total_deductions / delivered_revenue * 100) if delivered_revenue else 0.0

    summary = {
        "filename": filename,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "orders": int(len(df)),
        "delivered_orders": int(status.eq("Teslim Edildi").sum()),
        "delivered_revenue": delivered_revenue,
        "net_amount": _numeric_sum(df, "Net Tutar"),
        "commission": commission,
        "shipping": shipping,
        "return_shipping": return_shipping,
        "platform_fee": platform_fee,
        "penalty": penalty,
        "returns": returns,
        "total_deductions": total_deductions,
        "deduction_rate": deduction_rate,
        "suspicious_count": suspicious_count,
        "suspicious_amount": suspicious_amount,
    }
    raw = json.dumps(summary, ensure_ascii=False, sort_keys=True).encode("utf-8")
    summary["report_id"] = hashlib.sha1(raw).hexdigest()[:10].upper()
    return summary


def load_history() -> list[dict]:
    # V1.3 demo: history is kept only in the current browser session.
    # This avoids one demo user's report metadata being visible to another user.
    return list(st.session_state.get("pg_report_history", []))


def save_history_item(summary: dict) -> bool:
    history = load_history()
    if any(x.get("report_id") == summary.get("report_id") for x in history):
        return False
    history.insert(0, dict(summary))
    st.session_state["pg_report_history"] = history[:50]
    return True


def clear_history() -> None:
    st.session_state["pg_report_history"] = []


def money(v: float) -> str:
    return f"{v:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def _register_pdf_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("PGSans", path))
                return "PGSans"
    except Exception:
        pass
    return "Helvetica"


def build_pdf_report(summary: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    font = _register_pdf_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("PGTitle", parent=styles["Title"], fontName=font, fontSize=23, leading=28, textColor=colors.HexColor("#0B1220"), alignment=TA_LEFT, spaceAfter=8)
    sub = ParagraphStyle("PGSub", parent=styles["Normal"], fontName=font, fontSize=9.5, leading=14, textColor=colors.HexColor("#64748B"))
    h = ParagraphStyle("PGH", parent=styles["Heading2"], fontName=font, fontSize=12, textColor=colors.HexColor("#0B1220"), spaceBefore=14, spaceAfter=8)
    normal = ParagraphStyle("PGNormal", parent=styles["Normal"], fontName=font, fontSize=9.5, leading=14, textColor=colors.HexColor("#334155"))

    story = [
        Paragraph("ProfitGO Finansal Denetim Raporu", title),
        Paragraph(f"Rapor ID: {summary['report_id']} &nbsp;&nbsp; | &nbsp;&nbsp; Kaynak: {summary['filename']} &nbsp;&nbsp; | &nbsp;&nbsp; Tarih: {summary['generated_at']}", sub),
        Spacer(1, 14),
    ]

    data = [
        ["Toplam Siparis", f"{summary['orders']:,}"],
        ["Teslim Edilen", f"{summary['delivered_orders']:,}"],
        ["Teslim Edilen Ciro", money(summary['delivered_revenue'])],
        ["Net Finansal Tutar", money(summary['net_amount'])],
        ["Toplam Kesinti", money(summary.get('total_deductions', 0))],
        ["Kesinti Orani", f"%{summary.get('deduction_rate', 0):.2f}"],
        ["Komisyon", money(summary['commission'])],
        ["Gonderi Kargo", money(summary['shipping'])],
        ["Iade Kargo", money(summary['return_shipping'])],
        ["Platform Bedeli", money(summary['platform_fee'])],
        ["Toplam Ceza", money(summary['penalty'])],
        ["Incelenecek Kayit", str(summary['suspicious_count'])],
        ["Incelenecek Tutar", money(summary['suspicious_amount'])],
    ]
    table = Table(data, colWidths=[220, 220])
    table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), font),
        ("FONTSIZE", (0,0), (-1,-1), 9.5),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor("#334155")),
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story += [Paragraph("Finansal Ozet", h), table]

    risk_text = (
        f"ProfitGO, bu raporda {summary['suspicious_count']} kaydi detay inceleme icin one cikardi. "
        f"Toplam inceleme tutari {money(summary['suspicious_amount'])}. "
        "Bu rapor bir finansal kontrol destegidir; resmi muhasebe veya vergi kaydi yerine gecmez."
    )
    story += [Paragraph("Denetim Notu", h), Paragraph(risk_text, normal)]
    doc.build(story)
    return buffer.getvalue()
