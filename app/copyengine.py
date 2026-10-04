"""Copy engine: Glider enroll -> fund -> start -> rebalance -> positions.

Real path (GLIDER_API_KEY set, demo owner address known):
  begin_enrollment -> user signs (tiny sign page, iMessage can't sign EIP-712)
  -> complete_enrollment -> fund smart account -> start -> rebalance (poll op)
Degraded path (no key yet): structured blocked + exact next step, never a fake fill.
"""
from __future__ import annotations

import sqlite3
import time

import httpx

from app import pilots
from app.config import settings

ENROLL_SIG = "/enroll/signature"
ENROLL = "/enroll"


def _h() -> dict:
    return {"x-api-key": settings.glider_api_key}


def ready() -> bool:
    return bool(settings.glider_api_key)


async def whoami(db_path: str) -> dict:
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(f"{settings.glider_base_url}/whoami", headers=_h())
        ms = int((time.perf_counter() - t0) * 1000)
        _log(db_path, "glider", r.status_code, f"whoami {ms}ms")
        r.raise_for_status()
        return r.json()


async def begin_enrollment(db_path: str, owner: str, strategy_id: str) -> dict:
    """Stage 1: returns {message, flowId, accountIndex, agentAccountId} for the user to sign."""
    body = {"ownerAccountId": f"eip155:0:{owner}", "strategyId": strategy_id,
            "chainIds": [56], "accountType": "ECDSA"}
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.post(f"{settings.glider_base_url}{ENROLL_SIG}", headers=_h(), json=body)
        _log(db_path, "glider-enroll-sig", r.status_code, f"stage1 chain 56 owner {owner[:10]}…")
        if r.status_code == 400:
            return {"ok": False, "error": r.text[:300]}
        r.raise_for_status()
        return {"ok": True, "stage1": body, "glider": r.json()}


async def complete_enrollment(db_path: str, stage1: dict, glider_stage1: dict,
                              signature: str, name: str) -> dict:
    """Stage 2: echo stage-1 fields byte-for-byte + signature. Returns portfolio + smart accounts."""
    g = glider_stage1.get("data", glider_stage1)
    body = {**stage1, "accountIndex": str(g["accountIndex"]),
            "agentAccountId": g["agentAccountId"], "signature": signature,
            "flowId": g["flowId"], "portfolioName": name}
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(f"{settings.glider_base_url}{ENROLL}", headers=_h(), json=body)
        _log(db_path, "glider-enroll", r.status_code, "stage2 submit")
        r.raise_for_status()
        return r.json()


async def start_and_rebalance(db_path: str, portfolio_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(f"{settings.glider_base_url}/portfolios/{portfolio_id}/start", headers=_h())
        _log(db_path, "glider-start", r.status_code, portfolio_id)
        r.raise_for_status()
        r = await c.post(f"{settings.glider_base_url}/portfolios/{portfolio_id}/rebalance", headers=_h())
        _log(db_path, "glider-rebalance", r.status_code, portfolio_id)
        r.raise_for_status()
        op = r.json().get("data", {}).get("operationId", "")
    return await poll_operation(db_path, portfolio_id, op)


async def poll_operation(db_path: str, portfolio_id: str, op_id: str,
                         tries: int = 30, every_s: int = 4) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as c:
        for _ in range(tries):
            r = await c.get(f"{settings.glider_base_url}/portfolios/{portfolio_id}/operations/{op_id}",
                            headers=_h())
            body = r.json()
            status = body.get("data", {}).get("status", "")
            if status in ("completed", "failed", "cancelled"):
                _log(db_path, "glider-op", status, f"{portfolio_id}/{op_id}")
                return body
            time.sleep(every_s)
    _log(db_path, "glider-op", "timeout", f"{portfolio_id}/{op_id}")
    return {"status": "timeout"}


async def positions(db_path: str, portfolio_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(f"{settings.glider_base_url}/portfolios/{portfolio_id}/positions", headers=_h())
        _log(db_path, "glider-positions", r.status_code, portfolio_id)
        r.raise_for_status()
        return r.json()


def record_copy(db_path: str, phone: str, pilot_id: str, status: str,
                portfolio_id: str = "", smart_account: str = "") -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO users (phone) VALUES (?) ON CONFLICT(phone) DO NOTHING", (phone,))
    conn.execute("INSERT INTO copies (user_phone, pilot_id, glider_portfolio_id, smart_account, status)"
                 " VALUES (?,?,?,?,?)", (phone, pilot_id, portfolio_id, smart_account, status))
    conn.commit()
    conn.close()


def start_copy_texts(phone: str, pilot_id: str, notional: float) -> list[str]:
    """Degraded-path copy start: honest about what happens next, no fake fill."""
    p = pilots.PILOTS[pilot_id]
    if not ready():
        record_copy(_db(), phone, pilot_id, "quoted")
        return [
            f"locked in: {p['label']} with ${notional:.0f}. {p['disclaimer']}",
            "enrollment opens wednesday once our copy engine key lands — you're first in line. "
            "i'll text you the second it's ready. want me to explain how the copy works while you wait?",
        ]
    return [f"locked in: {p['label']} with ${notional:.0f}. checking the copy engine now — one sec."]


def _db() -> str:
    return settings.db_path


def _log(db_path: str, system: str, status: int | str, note: str) -> None:
    import sqlite3 as s
    c = s.connect(db_path)
    c.execute("INSERT INTO events (kind, system, status, note) VALUES (?,?,?,?)",
              ("api", system, str(status), note))
    c.commit()
    c.close()
