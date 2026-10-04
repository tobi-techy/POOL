"""POOL agent. Receives normalized inbound events from the sidecar, replies via sidecar."""
import time
import urllib.request
import json as jsonlib

from fastapi import FastAPI, Header, HTTPException

from app.agent import reply
from app.config import settings
from app.db import init_db, log_event
from app.tools import binance as btools

app = FastAPI(title="pool-agent")


@app.on_event("startup")
def _startup() -> None:
    init_db(settings.db_path)


def _send_via_sidecar(phone: str, texts: list[str]) -> None:
    body = jsonlib.dumps({"phone": phone, "texts": texts}).encode()
    req = urllib.request.Request(
        f"{settings.sidecar_url}/send",
        data=body,
        headers={"Content-Type": "application/json", "x-sidecar-secret": settings.sidecar_secret},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/internal/inbound")
def inbound(payload: dict, x_sidecar_secret: str = Header(default="")) -> dict:
    if settings.sidecar_secret and x_sidecar_secret != settings.sidecar_secret:
        raise HTTPException(status_code=401, detail="bad sidecar secret")
    phone = str(payload.get("phone", "unknown"))
    text = str(payload.get("text", ""))
    log_event(settings.db_path, "user", "sidecar", "ok", f"inbound from {phone}: {text[:120]}")
    texts = reply(text, phone)
    log_event(settings.db_path, "api", "agent", "ok", f"reply {len(texts)} texts to {phone}")
    _send_via_sidecar(phone, texts)
    return {"ok": True, "sent": len(texts)}


@app.post("/hooks/spectrum")
def spectrum_hook(payload: dict) -> dict:
    """Direct Photon webhook fallback (same shape as sidecar forwards)."""
    return inbound(payload, x_sidecar_secret=settings.sidecar_secret)


@app.get("/debug/pilots")
async def debug_pilots() -> dict:
    t0 = time.perf_counter()
    try:
        rows, ms = await btools.fetch_ondo_bsc()
    except Exception as e:  # noqa: BLE001 — tonight we record, not crash
        log_event(settings.db_path, "api", "binance-rwa", "error", f"rwa list failed: {e}")
        return {"ok": False, "error": str(e)}
    log_event(settings.db_path, "api", "binance-rwa", "ok", f"{len(rows)} ondo/bsc rows", ms)
    return {"ok": True, "latency_ms": ms, "count_bsc": len(rows), "rows": rows[:25]}
