"""
Bybit Trades Sync — Cloudflare Workers entry point.
Using Cloudflare Workers native Response with pyodide.
"""

import json
from urllib.parse import urlparse, parse_qs
from js import Response
from pyodide.ffi import to_js


async def _run_sync(env):
    from bybit_client import fetch_all_trades
    from database import ensure_schema, upsert_trades_batch

    api_key = env.BYBIT_API_KEY
    api_secret = env.BYBIT_API_SECRET
    base_url = getattr(env, "BYBIT_BASE_URL", "https://api.bybit.com")
    db = env.DB

    await ensure_schema(db)
    trades = await fetch_all_trades(base_url=base_url, api_key=api_key, api_secret=api_secret)
    new_count = await upsert_trades_batch(db, trades)

    return {
        "success": True,
        "new_trades": new_count,
        "total_fetched": len(trades),
        "message": f"Synced {new_count} new trades out of {len(trades)} fetched.",
    }


def _json_response(data, status=200):
    """Create JSON response for Cloudflare Workers"""
    body = json.dumps(data)
    headers = to_js({"content-type": "application/json"})
    options = to_js({"status": status, "headers": headers})
    return Response.new(body, options)


async def on_fetch(request, env):
    from database import ensure_schema, get_recent_trades, get_trade_count
    
    try:
        method = request.method.upper()
        url = str(request.url)
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        
        # Parse query string
        query = parse_qs(parsed.query)

        if path == "/health":
            return _json_response({
                "status": "ok",
                "service": "bybit-trades-sync",
                "version": "1.0.0"
            })

        elif path == "/trades" and method == "GET":
            try:
                limit = int(query.get("limit", ["20"])[0])
                limit = min(limit, 200)
            except Exception:
                limit = 20

            db = env.DB
            await ensure_schema(db)
            rows = await get_recent_trades(db, limit=limit)
            total = await get_trade_count(db)
            
            return _json_response({
                "total": total,
                "limit": limit,
                "trades": rows
            })

        elif path == "/sync" and method == "POST":
            result = await _run_sync(env)
            return _json_response(result)

        else:
            return _json_response({
                "error": "Not found",
                "path": path
            }, status=404)

    except Exception as e:
        import traceback
        return _json_response({
            "error": str(e),
            "type": type(e).__name__
        }, status=500)


async def on_scheduled(event, env, ctx):
    try:
        result = await _run_sync(env)
        print(f"[cron] {result['message']}")
    except Exception as e:
        print(f"[cron-error] {e}")