"""SQLite schema. Positions are read live from Glider; this stores relationships."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS pilots (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  disclaimer TEXT NOT NULL,
  glider_strategy_id TEXT,
  version INTEGER DEFAULT 1,
  weights_json TEXT NOT NULL DEFAULT '{}',
  spread_limit_bps INTEGER DEFAULT 150,
  source TEXT DEFAULT 'ours'
);
CREATE TABLE IF NOT EXISTS users (
  phone TEXT PRIMARY KEY,
  owner_address TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS copies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_phone TEXT NOT NULL REFERENCES users(phone),
  pilot_id TEXT NOT NULL REFERENCES pilots(id),
  glider_portfolio_id TEXT,
  smart_account TEXT,
  status TEXT DEFAULT 'quoted',
  last_seen_version INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT DEFAULT (datetime('now')),
  kind TEXT NOT NULL,
  system TEXT NOT NULL,
  latency_ms INTEGER,
  status TEXT,
  note TEXT
);
CREATE TABLE IF NOT EXISTS confirms (
  token TEXT PRIMARY KEY,
  user_phone TEXT NOT NULL,
  pilot_id TEXT NOT NULL,
  notional_usd REAL NOT NULL,
  quote_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def log_event(path: str, kind: str, system: str, status: str, note: str, latency_ms: int | None = None) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO events (kind, system, latency_ms, status, note) VALUES (?,?,?,?,?)",
        (kind, system, latency_ms, status, note),
    )
    conn.commit()
    conn.close()
