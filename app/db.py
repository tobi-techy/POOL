"""SQLite schema + migrations. Positions are read live from Glider; this stores relationships."""
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
  stage TEXT DEFAULT 'new',
  picked_pilot TEXT DEFAULT '',
  pending_usd REAL DEFAULT 0,
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

_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN stage TEXT DEFAULT 'new'",
    "ALTER TABLE users ADD COLUMN picked_pilot TEXT DEFAULT ''",
    "ALTER TABLE users ADD COLUMN pending_usd REAL DEFAULT 0",
]


def init_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for sql in _MIGRATIONS:
        col = sql.split("ADD COLUMN")[1].split()[0]
        if col not in cols:
            conn.execute(sql)
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


def get_user(path: str, phone: str) -> dict:
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO users (phone) VALUES (?) ON CONFLICT(phone) DO NOTHING", (phone,))
    conn.commit()
    row = conn.execute("SELECT phone, owner_address, stage, picked_pilot, pending_usd FROM users WHERE phone=?",
                       (phone,)).fetchone()
    conn.close()
    return {"phone": row[0], "owner_address": row[1], "stage": row[2] or "new",
            "picked_pilot": row[3] or "", "pending_usd": row[4] or 0}


def set_user(path: str, phone: str, **kw: object) -> None:
    conn = sqlite3.connect(path)
    for k, v in kw.items():
        conn.execute(f"UPDATE users SET {k}=? WHERE phone=?", (v, phone))
    conn.commit()
    conn.close()


def user_copies(path: str, phone: str) -> list[dict]:
    conn = sqlite3.connect(path)
    rows = conn.execute("SELECT pilot_id, glider_portfolio_id, smart_account, status FROM copies "
                        "WHERE user_phone=? ORDER BY id DESC", (phone,)).fetchall()
    conn.close()
    return [{"pilot_id": r[0], "portfolio_id": r[1], "smart_account": r[2], "status": r[3]} for r in rows]
