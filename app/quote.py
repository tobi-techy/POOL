"""Quote + spread guard. A confirm token is issued ONLY from live prices.

Degraded mode (Binance unreachable): legs are shown as indicative from the
seed watchlist with no prices, and no confirm token is issued. We would rather
refuse a copy than quote a number we did not observe.
"""
from __future__ import annotations

import re
import secrets
import sqlite3
import time
from dataclasses import dataclass, field

from app import pilots
from app.config import settings
from app.tools import binance as btools

CONFIRM_TTL_S = 10 * 60


@dataclass
class Leg:
    ticker: str
    symbol: str | None = None
    contract: str | None = None
    multiplier: str | None = None
    onchain_price: str | None = None
    ref_price: str | None = None
    spread_bps: int | None = None
    tradable: bool | None = None
    pause_reason: str | None = None


@dataclass
class Quote:
    ok: bool
    pilot_id: str
    notional_usd: float
    legs: list[Leg] = field(default_factory=list)
    market_open: bool | None = None
    blocked_reason: str | None = None
    needs_second_confirm: bool = False
    quote_id: str = ""


WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}


def parse_amount(text: str) -> float | None:
    t = text.strip().lower()
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)", t)
    if m:
        try:
            v = float(m.group(1))
            return v if v > 0 else None
        except ValueError:
            pass
    for w, v in WORDS.items():
        if re.search(rf"\b{w}\b", t):
            return float(v)
    return None


async def build_quote(pilot_id: str, notional: float, db_path: str) -> Quote:
    """Live-quote path. Falls back to indicative (ok=False) when Binance is down."""
    if notional > settings.max_copy_usd:
        return Quote(ok=False, pilot_id=pilot_id, notional_usd=notional,
                     blocked_reason=f"over the ${settings.max_copy_usd:.0f} demo cap per copy")
    try:
        rows, ms = await btools.fetch_ondo_bsc(timeout_s=12.0)
    except Exception as e:  # noqa: BLE001 — degraded, not dead
        _log(db_path, "binance-rwa", "error", f"quote fetch failed: {e}")
        return Quote(ok=False, pilot_id=pilot_id, notional_usd=notional,
                     blocked_reason="prices_unavailable")
    _log(db_path, "binance-rwa", "ok", f"quote list: {len(rows)} bsc rows", ms)
    by_ticker = {r.get("ticker"): r for r in rows}
    quote = Quote(ok=True, pilot_id=pilot_id, notional_usd=notional,
                  quote_id=secrets.token_hex(6))
    for leg in pilots.legs_for(pilot_id) or []:
        t = leg.get("ticker", "?")
        r = by_ticker.get(t)
        if not r:
            quote.legs.append(Leg(ticker=t, tradable=False, pause_reason="no BSC contract right now"))
            continue
        quote.legs.append(Leg(ticker=t, symbol=r.get("symbol"),
                              contract=r.get("contractAddress"),
                              multiplier=r.get("multiplier")))
    # trade-status + price enrichment lands here with the API key
    # (market status, per-asset pause, on-chain vs reference). Until then a
    # quote with legs but no observed prices cannot arm a confirm token:
    if not quote.legs:
        quote.ok = False
        quote.blocked_reason = "no validated legs yet"
    return quote


def confirm_text(q: Quote) -> list[str]:
    if not q.ok and q.blocked_reason == "prices_unavailable":
        p = pilots.PILOTS[q.pilot_id]
        return [f"i want to quote you {p['label']} ${q.notional_usd:.0f} but live prices aren't loading right now, so i'm not going to make up numbers. try again in a bit — i've logged it. still want {p['label']} when they're back?"]
    if not q.ok:
        return [f"can't quote that yet: {q.blocked_reason}. want to pick a different pilot?"]
    legs = ", ".join(l.ticker for l in q.legs)
    guard = ""
    if q.market_open is False:
        guard = " us market's shut, so tokenized prices can drift from the real ones — "
    second = " reply YES to confirm, and if the spread's wide i'll ask you twice." if q.needs_second_confirm else " reply YES to copy, anything else to change it."
    return [f"ok: {pilots.PILOTS[q.pilot_id]['label']} with ${q.notional_usd:.0f} — {legs}.{guard}{second}"]


def _log(db_path: str, system: str, status: str, note: str, ms: int | None = None) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO events (kind, system, latency_ms, status, note) VALUES (?,?,?,?,?)",
                 ("api", system, ms, status, note))
    conn.commit()
    conn.close()


def arm_confirm(db_path: str, phone: str, q: Quote) -> str:
    token = secrets.token_hex(8)
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO confirms (token, user_phone, pilot_id, notional_usd, quote_id) VALUES (?,?,?,?,?)",
                 (token, phone, q.pilot_id, q.notional_usd, q.quote_id))
    conn.commit()
    conn.close()
    return token


def take_confirm(db_path: str, phone: str) -> dict | None:
    """Returns the live confirm for this phone or None (missing/expired/consumed)."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT token, pilot_id, notional_usd, quote_id, created_at FROM confirms "
        "WHERE user_phone=? ORDER BY created_at DESC LIMIT 1", (phone,)).fetchone()
    if not row:
        conn.close()
        return None
    token, pid, notion, qid, created = row
    age = time.time() - time.mktime(time.strptime(created, "%Y-%m-%d %H:%M:%S"))
    conn.execute("DELETE FROM confirms WHERE token=?", (token,))  # single use
    conn.commit()
    conn.close()
    if age > CONFIRM_TTL_S:
        return None
    return {"token": token, "pilot_id": pid, "notional_usd": notion, "quote_id": qid}
