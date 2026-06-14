"""
Bybit Trades Sync — Cloudflare Workers entry point.

HTTP routes (FastAPI / ASGI):
  GET  /health        — liveness probe
  GET  /trades        — list recent stored trades
  POST /sync          — manually trigger a sync

Scheduled trigger (cron every 6 hours):
  on_scheduled        — automatically called by Cloudflare cron
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.bybit_client import fetch_all_trades
from src.database import ensure_schema, get_recent_trades, get_trade_count, upsert_trades_batch
from src.models import HealthResponse, SyncResult

app = FastAPI(
    title="Bybit Trades Sync",
    description="Syncs Bybit execution history to Cloudflare D1 every 6 hours.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_from_scope(request: Request):
    """Extract Cloudflare Workers env bindings from the ASGI scope."""
    return request.scope.get("cloudflare.workers.env")


async def _run_sync(env) -> SyncResult:
    """Core sync logic: fetch from Bybit → upsert into D1."""
    api_key: str = env.BYBIT_API_KEY
    api_secret: str = env.BYBIT_API_SECRET
    base_url: str = getattr(env, "BYBIT_BASE_URL", "https://api.bybit.com")
    db = env.DB

    await ensure_schema(db)

    trades = await fetch_all_trades(
        base_url=base_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    new_count = await upsert_trades_batch(db, trades)

    return SyncResult(
        success=True,
        new_trades=new_count,
        total_fetched=len(trades),
        message=f"Synced {new_count} new trades out of {len(trades)} fetched.",
    )


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="bybit-trades-sync",
        version="1.0.0",
    )


@app.get("/trades")
async def list_trades(request: Request, limit: int = 20):
    env = _env_from_scope(request)
    if env is None:
        return JSONResponse({"error": "env bindings not available"}, status_code=500)

    db = env.DB
    await ensure_schema(db)

    rows = await get_recent_trades(db, limit=min(limit, 200))
    total = await get_trade_count(db)
    return JSONResponse({"total": total, "limit": limit, "trades": rows})


@app.post("/sync", response_model=SyncResult)
async def manual_sync(request: Request):
    env = _env_from_scope(request)
    if env is None:
        return JSONResponse({"error": "env bindings not available"}, status_code=500)

    result = await _run_sync(env)
    return JSONResponse(result.model_dump())


# ---------------------------------------------------------------------------
# Cloudflare Scheduled Trigger (cron every 6 hours)
# ---------------------------------------------------------------------------

async def on_scheduled(event, env, ctx):
    """
    Called automatically by Cloudflare Workers cron trigger.
    wrangler.toml: crons = ["0 */6 * * *"]
    """
    result = await _run_sync(env)
    print(f"[cron] {result.message}")
