"""Seed pilots/seed.json from the live Binance Ondo list (BSC only)."""
import asyncio
import json
import sys

sys.path.insert(0, ".")

from app.tools import binance as btools

PELOSI_WATCH = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "META", "GOOGL", "AMZN"]
BUFFETT_WATCH = ["AAPL", "BAC", "KO", "AXP", "CVX", "OXY", "MCO", "AON"]
CHIPS_WATCH = ["NVDA", "AMD", "AVGO", "LRCX", "AMAT", "MU"]


async def main() -> None:
    rows, ms = await btools.fetch_ondo_bsc()
    by_ticker = {r.get("ticker"): r for r in rows}
    print(f"ondo bsc rows: {len(rows)} in {ms}ms")

    def legs(watch: list[str]) -> list[dict]:
        out = []
        for t in watch:
            r = by_ticker.get(t)
            if r:
                out.append(
                    {
                        "ticker": t,
                        "symbol": r.get("symbol"),
                        "chainId": "56",
                        "contractAddress": r.get("contractAddress"),
                        "multiplier": r.get("multiplier"),
                    }
                )
        return out

    seed = {
        "pelosi-style": {"note": "from public disclosures, delayed", "legs": legs(PELOSI_WATCH)},
        "buffett-style": {"note": "from 13f filings, delayed", "legs": legs(BUFFETT_WATCH)},
        "ai-chips": {"note": "thematic", "legs": legs(CHIPS_WATCH)},
    }
    with open("pilots/seed.json", "w") as f:
        json.dump(seed, f, indent=2)
    print("wrote pilots/seed.json")
    for k, v in seed.items():
        print(f"- {k}: {len(v['legs'])} legs")


asyncio.run(main())
