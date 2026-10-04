"""Binance Web3 read layer. Tonight: public RWA list + status. Quote/simulate land with the key."""
import time

import httpx

RWA_LIST_URL = (
    "https://www.binance.com/bapi/defi/v1/public/wallet-direct/"
    "buw/wallet/market/token/rwa/stock/detail/list/ai"
)

HEADERS = {"Accept-Encoding": "identity", "User-Agent": "pool-hackathon/0.1"}


async def fetch_ondo_bsc(timeout_s: float = 20.0) -> tuple[list[dict], int]:
    """Returns (ondo-on-BSC rows, latency_ms). Raises on network failure."""
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout_s, headers=HEADERS) as c:
        r = await c.get(RWA_LIST_URL, params={"type": 1})
        r.raise_for_status()
        body = r.json()
    ms = int((time.perf_counter() - t0) * 1000)
    rows = [x for x in body.get("data", []) if str(x.get("chainId")) == "56"]
    return rows, ms


def summarize(rows: list[dict], tickers: list[str]) -> str:
    by_ticker = {r.get("ticker"): r for r in rows}
    lines = []
    for t in tickers:
        r = by_ticker.get(t)
        if not r:
            lines.append(f"{t}: not on BSC Ondo right now")
        else:
            lines.append(f"{t}: {r.get('symbol')} {str(r.get('contractAddress'))[:10]}… mult {r.get('multiplier')}")
    return "\n".join(lines)
