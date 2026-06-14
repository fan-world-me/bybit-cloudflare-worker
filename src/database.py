"""
Cloudflare D1 database operations for Bybit trades.
"""
import asyncio
from typing import Any


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exec_id         TEXT    NOT NULL UNIQUE,
    order_id        TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    category        TEXT    NOT NULL DEFAULT 'spot',
    side            TEXT    NOT NULL,
    order_type      TEXT    NOT NULL,
    exec_price      TEXT    NOT NULL,
    exec_qty        TEXT    NOT NULL,
    exec_value      TEXT    NOT NULL,
    exec_fee        TEXT    NOT NULL,
    fee_currency    TEXT    NOT NULL DEFAULT '',
    exec_time       TEXT    NOT NULL,
    order_link_id   TEXT,
    stop_order_type TEXT,
    created_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_trades_symbol    ON trades(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_trades_exec_time ON trades(exec_time DESC);",
    "CREATE INDEX IF NOT EXISTS idx_trades_category  ON trades(category);",
]


async def ensure_schema(db) -> None:
    """Create table and indexes if they do not exist yet."""
    await db.exec(CREATE_TABLE_SQL).run()
    for stmt in CREATE_INDEXES_SQL:
        await db.exec(stmt).run()


async def upsert_trade(db, trade: dict) -> bool:
    """
    Insert a single trade. Returns True if new row inserted,
    False if already existed (exec_id conflict → ignored).
    """
    sql = """
        INSERT OR IGNORE INTO trades
            (exec_id, order_id, symbol, category, side, order_type,
             exec_price, exec_qty, exec_value, exec_fee, fee_currency,
             exec_time, order_link_id, stop_order_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    values = [
        str(trade.get("execId", "")),
        str(trade.get("orderId", "")),
        str(trade.get("symbol", "")),
        str(trade.get("category", "spot")),
        str(trade.get("side", "")),
        str(trade.get("orderType", "")),
        str(trade.get("execPrice", "0")),
        str(trade.get("execQty", "0")),
        str(trade.get("execValue", "0")),
        str(trade.get("execFee", "0")),
        str(trade.get("feeCurrency", "")),
        str(trade.get("execTime", "")),
        trade.get("orderLinkId"),
        trade.get("stopOrderType"),
    ]

    stmt = db.prepare(sql).bind(*values)
    result = await stmt.run()
    changes = getattr(result, "changes", 0) or 0
    return int(changes) > 0


async def upsert_trades_batch(db, trades: list[dict]) -> int:
    """Asynchronously insert all trades; return count of newly inserted rows."""
    tasks = [upsert_trade(db, t) for t in trades]
    results = await asyncio.gather(*tasks)
    return sum(1 for inserted in results if inserted)


async def get_trade_count(db) -> int:
    """Return total number of stored trades."""
    result = await db.prepare("SELECT COUNT(*) AS cnt FROM trades").first()
    return int(getattr(result, "cnt", 0) or 0)


async def get_recent_trades(db, limit: int = 20) -> list[dict]:
    """Return the most recent trades ordered by exec_time descending."""
    result = await db.prepare(
        "SELECT * FROM trades ORDER BY exec_time DESC LIMIT ?"
    ).bind(str(limit)).all()

    rows = getattr(result, "results", []) or []
    return [dict(r) for r in rows]
