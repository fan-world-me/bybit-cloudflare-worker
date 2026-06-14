"""
Bybit REST API v5 async client for Cloudflare Workers Python runtime.
Uses JavaScript fetch() interop for outbound HTTP requests.
"""
import hashlib
import hmac
import json
import time
from typing import Any, Optional
from urllib.parse import urlencode

from js import fetch, Object
from pyodide.ffi import to_js


RECV_WINDOW = "5000"


def _sign(api_secret: str, payload: str) -> str:
    return hmac.new(
        api_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_headers(api_key: str, api_secret: str, timestamp: str, query_string: str) -> dict:
    sign_payload = timestamp + api_key + RECV_WINDOW + query_string
    signature = _sign(api_secret, sign_payload)
    return {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "Content-Type": "application/json",
    }


async def _get(base_url: str, path: str, api_key: str, api_secret: str, params: dict) -> dict:
    timestamp = str(int(time.time() * 1000))
    query_string = urlencode(params)
    headers = _build_headers(api_key, api_secret, timestamp, query_string)

    url = f"{base_url}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    js_headers = to_js(headers, dict_converter=Object.fromEntries)
    js_init = to_js({"method": "GET", "headers": js_headers}, dict_converter=Object.fromEntries)
    response = await fetch(url, js_init)
    text = await response.text()
    return json.loads(text)


async def fetch_trades(
    base_url: str,
    api_key: str,
    api_secret: str,
    category: str = "spot",
    symbol: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> dict:
    params: dict[str, Any] = {
        "category": category,
        "limit": limit,
    }
    if symbol:
        params["symbol"] = symbol
    if cursor:
        params["cursor"] = cursor

    return await _get(base_url, "/v5/execution/list", api_key, api_secret, params)


async def fetch_all_trades(
    base_url: str,
    api_key: str,
    api_secret: str,
    categories: list[str] | None = None,
    limit: int = 50,
) -> list[dict]:
    if categories is None:
        categories = ["spot", "linear", "inverse"]

    all_trades: list[dict] = []

    for category in categories:
        cursor = None
        while True:
            result = await fetch_trades(
                base_url=base_url,
                api_key=api_key,
                api_secret=api_secret,
                category=category,
                limit=limit,
                cursor=cursor,
            )

            if result.get("retCode") != 0:
                print(f"[bybit] category={category} error: {result.get('retMsg')}")
                break

            data = result.get("result", {})
            rows = data.get("list", [])

            for row in rows:
                row["category"] = category
                all_trades.append(row)

            cursor = data.get("nextPageCursor")
            if not cursor:
                break

    return all_trades
