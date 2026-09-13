from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any

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
    headers = {
        "User-Agent": creds.user_agent,
        "Accept": "application/json",
    }
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            auth=HTTPBasicAuth(creds.api_key, creds.api_secret),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise TrendyolApiError(f"Trendyol API bağlantısı kurulamadı: {exc}") from exc

    if response.status_code == 401:
        raise TrendyolApiError("Trendyol API yetkilendirmesi başarısız (401). API Key / Secret / Satıcı ID bilgilerini kontrol et.")
    if response.status_code == 429:
        raise TrendyolApiError("Trendyol API istek limiti aşıldı (429). Birkaç dakika sonra tekrar dene.")
    if not response.ok:
        body = response.text[:500]
        raise TrendyolApiError(f"Trendyol API hata verdi ({response.status_code}): {body}")

    try:
        return response.json()
    except ValueError as exc:
        raise TrendyolApiError("Trendyol API geçerli JSON döndürmedi.") from exc


def fetch_order_packages(
    creds: TrendyolCredentials,
    start_date: date,
    end_date: date,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all shipment packages in the selected period via Order V2 endpoint."""
    start_ms = _to_ms(start_date)
    end_ms = _to_ms(end_date, end_of_day=True)
    page = 0
    size = 200
    packages: list[dict[str, Any]] = []

    while True:
        params: dict[str, Any] = {
            "startDate": start_ms,
            "endDate": end_ms,
            "page": page,
            "size": size,
            "orderByField": "PackageLastModifiedDate",
            "orderByDirection": "ASC",
        }
        if status:
            params["status"] = status

        data = _request(
            creds,
            f"/integration/order/sellers/{creds.seller_id}/v2/orders",
            params,
        )
        content = data.get("content") or []
        packages.extend(content)

        total_pages = data.get("totalPages")
        if total_pages is not None:
            if page + 1 >= int(total_pages):
                break
        elif len(content) < size:
            break

        page += 1
        if page > 1000:
            raise TrendyolApiError("Beklenmeyen sayfalama döngüsü durduruldu.")

    return packages


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


def test_connection(creds: TrendyolCredentials) -> tuple[bool, str]:
    today = datetime.now(timezone.utc).date()
    try:
        fetch_order_packages(creds, today, today)
        return True, "Trendyol API bağlantısı başarılı."
    except TrendyolApiError as exc:
        return False, str(exc)
