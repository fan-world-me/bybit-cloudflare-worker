-- Bybit Trades Sync — Cloudflare D1 Schema
-- Run with: wrangler d1 execute bybit-trades --file=schema.sql

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

CREATE INDEX IF NOT EXISTS idx_trades_symbol    ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_exec_time ON trades(exec_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_category  ON trades(category);
