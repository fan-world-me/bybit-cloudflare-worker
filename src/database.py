"""
Cloudflare D1 database operations for Bybit trades.
"""
import asyncio


async def ensure_schema(db) -> None:
    """Create table and indexes if they do not exist yet."""
    try:
        await db.exec(
            "CREATE TABLE IF NOT EXISTS trades ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "exec_id TEXT NOT NULL UNIQUE, "
            "order_id TEXT NOT NULL, "
            "symbol TEXT NOT NULL, "
            "category TEXT NOT NULL DEFAULT 'spot', "
            "side TEXT NOT NULL, "
            "order_type TEXT NOT NULL, "
            "exec_price TEXT NOT NULL, "
            "exec_qty TEXT NOT NULL, "
            "exec_value TEXT NOT NULL, "
            "exec_fee TEXT NOT NULL, "
            "fee_currency TEXT NOT NULL DEFAULT '', "
            "exec_time TEXT NOT NULL, "
            "order_link_id TEXT, "
            "stop_order_type TEXT, "
            "created_at INTEGER NOT NULL DEFAULT (unixepoch())"
            ")"
        )
        
        await db.exec("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        await db.exec("CREATE INDEX IF NOT EXISTS idx_trades_exec_time ON trades(exec_time DESC)")
        await db.exec("CREATE INDEX IF NOT EXISTS idx_trades_category ON trades(category)")
        
        print("[db] Schema initialized")
    except Exception as e:
        print(f"[db] Schema error: {e}")


async def upsert_trade(db, trade: dict) -> bool:
    """Insert a single trade."""
    sql = (
        "INSERT OR IGNORE INTO trades "
        "(exec_id, order_id, symbol, category, side, order_type, "
        "exec_price, exec_qty, exec_value, exec_fee, fee_currency, "
        "exec_time, order_link_id, stop_order_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    
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

    try:
        stmt = db.prepare(sql)
        for v in values:
            stmt = stmt.bind(v if v is not None else None)
        await stmt.all()
        return True
    except Exception as e:
        print(f"[db] Insert error: {e}")
        return False


async def upsert_trades_batch(db, trades: list) -> int:
    """Insert all trades asynchronously."""
    if not trades:
        return 0
    
    tasks = [upsert_trade(db, t) for t in trades]
    results = await asyncio.gather(*tasks)
    return sum(1 for inserted in results if inserted)


async def get_trade_count(db) -> int:
    """Return total number of stored trades."""
    try:
        result = await db.prepare("SELECT COUNT(*) AS cnt FROM trades").all()
        if result and hasattr(result, 'results') and result.results:
            return int(result.results[0].get("cnt", 0))
        return 0
    except Exception as e:
        print(f"[db] Count error: {e}")
        return 0


async def get_recent_trades(db, limit: int = 20) -> list:
    """Return recent trades ordered by exec_time descending."""
    try:
        result = await db.prepare(
            "SELECT * FROM trades ORDER BY exec_time DESC LIMIT ?"
        ).bind(str(limit)).all()

        if result and hasattr(result, 'results'):
            return [dict(r) for r in result.results] if result.results else []
        return []
    except Exception as e:
        print(f"[db] Fetch error: {e}")
        return []