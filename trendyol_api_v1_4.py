from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Iterable

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://apigw.trendyol.com"


@dataclass(frozen=True)
class TrendyolCredentials:
    seller_id: int
    api_key: str
    api_secret: str
    user_agent: str


class TrendyolApiError(RuntimeError):
    pass


def _to_ms(value: date, end_of_day: bool = False) -> int:
    t = time.max if end_of_day else time.min
    dt = datetime.combine(value, t).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _request(creds: TrendyolCredentials, path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": creds.user_agent, "Accept": "application/json"}
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            auth=HTTPBasicAuth(creds.api_key, creds.api_secret),
            timeout=45,
        )
    except requests.RequestException as exc:
        raise TrendyolApiError(f"Trendyol API bağlantısı kurulamadı: {exc}") from exc

    if response.status_code == 401:
        raise TrendyolApiError("Trendyol API yetkilendirmesi başarısız (401). API Key / Secret / Satıcı ID bilgilerini kontrol et.")
    if response.status_code == 429:
        raise TrendyolApiError("Trendyol API istek limiti aşıldı (429). Birkaç dakika sonra tekrar dene.")
    if not response.ok:
        body = response.text[:800]
        raise TrendyolApiError(f"Trendyol API hata verdi ({response.status_code}): {body}")

    try:
        return response.json()
    except ValueError as exc:
        raise TrendyolApiError("Trendyol API geçerli JSON döndürmedi.") from exc


def _paged_content(
    creds: TrendyolCredentials,
    path: str,
    params: dict[str, Any],
    *,
    size: int = 1000,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    page = 0
    rows: list[dict[str, Any]] = []
    while True:
        page_params = dict(params)
        page_params.update({"page": page, "size": size})
        data = _request(creds, path, page_params)
        content = data.get("content") or []
        if source_type:
            for item in content:
                item = dict(item)
                item["_sourceTransactionType"] = source_type
                rows.append(item)
        else:
            rows.extend(content)

        total_pages = data.get("totalPages")
        if total_pages is not None:
            if page + 1 >= int(total_pages):
                break
        elif len(content) < size:
            break
        page += 1
        if page > 2000:
            raise TrendyolApiError("Beklenmeyen finans sayfalama döngüsü durduruldu.")
    return rows


def fetch_order_packages(
    creds: TrendyolCredentials,
    start_date: date,
    end_date: date,
    status: str | None = None,
) -> list[dict[str, Any]]:
    start_ms = _to_ms(start_date)
    end_ms = _to_ms(end_date, end_of_day=True)
    params: dict[str, Any] = {
        "startDate": start_ms,
        "endDate": end_ms,
        "orderByField": "PackageLastModifiedDate",
        "orderByDirection": "ASC",
    }
    if status:
        params["status"] = status
    return _paged_content(
        creds,
        f"/integration/order/sellers/{creds.seller_id}/v2/orders",
        params,
        size=200,
    )


def packages_to_lines(packages: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for package in packages:
        order_number = str(package.get("orderNumber") or "")
        package_id = package.get("shipmentPackageId") or package.get("id")
        package_status = package.get("status") or package.get("shipmentPackageStatus") or ""
        order_date = package.get("orderDate") or package.get("createdDate") or package.get("packageLastModifiedDate")
        for line in package.get("lines") or []:
            quantity = float(line.get("quantity") or 0)
            gross_unit = float(line.get("lineGrossAmount") or line.get("price") or 0)
            unit_price = float(line.get("lineUnitPrice") or line.get("price") or 0)
            seller_discount_unit = float(line.get("lineSellerDiscount") or 0)
            ty_discount_unit = float(line.get("lineTyDiscount") or 0)
            commission_rate = float(line.get("commission") or line.get("commissionRate") or 0)
            vat_rate = float(line.get("vatRate") or 0)
            rows.append({
                "Sipariş No": order_number,
                "Paket ID": package_id,
                "Sipariş Tarihi": order_date,
                "Sipariş Statüsü": package_status,
                "Model Kodu": str(line.get("stockCode") or line.get("merchantSku") or "").strip(),
                "Barkod": str(line.get("barcode") or "").strip(),
                "Ürün Adı": str(line.get("productName") or "").strip(),
                "Ürün Adedi": quantity,
                "Birim Brüt Fiyat": gross_unit,
                "Birim Net Fiyat": unit_price,
                "Teslim Ciro": unit_price * quantity,
                "Satıcı İndirimi": seller_discount_unit * quantity,
                "Trendyol İndirimi": ty_discount_unit * quantity,
                "Komisyon Oranı %": commission_rate,
                "Tahmini Komisyon": (unit_price * quantity) * (commission_rate / 100.0),
                "KDV Oranı %": vat_rate,
                "Line ID": line.get("lineId"),
            })
    return pd.DataFrame(rows)


SETTLEMENT_TYPES = (
    "Sale",
    "Return",
    "Discount",
    "DiscountCancel",
    "Coupon",
    "CouponCancel",
    "ProvisionPositive",
    "ProvisionNegative",
    "SellerRevenuePositive",
    "SellerRevenueNegative",
    "CommissionPositive",
    "CommissionNegative",
    "SellerRevenuePositiveCancel",
    "SellerRevenueNegativeCancel",
    "CommissionPositiveCancel",
    "CommissionNegativeCancel",
)


def fetch_settlements(
    creds: TrendyolCredentials,
    start_date: date,
    end_date: date,
    transaction_types: Iterable[str] = SETTLEMENT_TYPES,
) -> pd.DataFrame:
    """Fetch Trendyol current-account settlement records. Date range must be <= 15 days."""
    if (end_date - start_date).days > 14:
        raise TrendyolApiError("Finans servisi tek sorguda en fazla 15 günlük tarih aralığı kabul ediyor.")
    all_rows: list[dict[str, Any]] = []
    base_params = {"startDate": _to_ms(start_date), "endDate": _to_ms(end_date, end_of_day=True)}
    path = f"/integration/finance/che/sellers/{creds.seller_id}/settlements"
    for transaction_type in transaction_types:
        params = dict(base_params)
        params["transactionType"] = transaction_type
        try:
            all_rows.extend(_paged_content(creds, path, params, size=1000, source_type=transaction_type))
        except TrendyolApiError as exc:
            # Some seller accounts may not expose every correction type. Core Sale/Return must still fail loudly.
            if transaction_type in {"Sale", "Return"}:
                raise
            if "400" not in str(exc):
                raise
    return pd.DataFrame(all_rows)


def fetch_other_financials(
    creds: TrendyolCredentials,
    start_date: date,
    end_date: date,
    transaction_type: str = "DeductionInvoices",
    transaction_sub_type: str | None = None,
) -> pd.DataFrame:
    if (end_date - start_date).days > 14:
        raise TrendyolApiError("Finans servisi tek sorguda en fazla 15 günlük tarih aralığı kabul ediyor.")
    params: dict[str, Any] = {
        "startDate": _to_ms(start_date),
        "endDate": _to_ms(end_date, end_of_day=True),
        "transactionType": transaction_type,
    }
    if transaction_sub_type:
        params["transactionSubType"] = transaction_sub_type
    rows = _paged_content(
        creds,
        f"/integration/finance/che/sellers/{creds.seller_id}/otherfinancials",
        params,
        size=1000,
        source_type=transaction_type,
    )
    return pd.DataFrame(rows)


def settlement_summary(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "seller_revenue_net": 0.0,
            "commission_net": 0.0,
            "sales_revenue": 0.0,
            "return_revenue": 0.0,
            "sale_commission": 0.0,
            "return_commission": 0.0,
        }

    work = df.copy()
    for col in ("sellerRevenue", "commissionAmount", "debt", "credit"):
        if col not in work.columns:
            work[col] = 0.0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)

    source = work.get("_sourceTransactionType", pd.Series("", index=work.index)).astype(str)
    revenue_sign = source.map({
        "Sale": 1, "Return": -1, "Discount": -1, "DiscountCancel": 1,
        "Coupon": -1, "CouponCancel": 1, "ProvisionPositive": 1, "ProvisionNegative": -1,
        "SellerRevenuePositive": 1, "SellerRevenueNegative": -1,
        "SellerRevenuePositiveCancel": -1, "SellerRevenueNegativeCancel": 1,
    }).fillna(0.0)
    commission_sign = source.map({
        "Sale": 1, "Return": -1, "Discount": -1, "DiscountCancel": 1,
        "Coupon": -1, "CouponCancel": 1, "ProvisionPositive": 1, "ProvisionNegative": -1,
        "CommissionPositive": 1, "CommissionNegative": -1,
        "CommissionPositiveCancel": -1, "CommissionNegativeCancel": 1,
    }).fillna(0.0)

    seller_revenue_net = float((work["sellerRevenue"].abs() * revenue_sign).sum())
    commission_net = float((work["commissionAmount"].abs() * commission_sign).sum())
    return {
        "seller_revenue_net": seller_revenue_net,
        "commission_net": commission_net,
        "sales_revenue": float(work.loc[source.eq("Sale"), "sellerRevenue"].abs().sum()),
        "return_revenue": float(work.loc[source.eq("Return"), "sellerRevenue"].abs().sum()),
        "sale_commission": float(work.loc[source.eq("Sale"), "commissionAmount"].abs().sum()),
        "return_commission": float(work.loc[source.eq("Return"), "commissionAmount"].abs().sum()),
    }


def other_financial_summary(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {"debt": 0.0, "credit": 0.0, "net_deduction": 0.0}
    debt = pd.to_numeric(df.get("debt", 0.0), errors="coerce").fillna(0.0)
    credit = pd.to_numeric(df.get("credit", 0.0), errors="coerce").fillna(0.0)
    return {"debt": float(debt.sum()), "credit": float(credit.sum()), "net_deduction": float(debt.sum() - credit.sum())}


def test_connection(creds: TrendyolCredentials) -> tuple[bool, str]:
    today = datetime.now(timezone.utc).date()
    try:
        fetch_order_packages(creds, today, today)
        return True, "Trendyol API bağlantısı başarılı."
    except TrendyolApiError as exc:
        return False, str(exc)
