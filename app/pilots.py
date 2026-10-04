"""Pilot catalog. Loads pilots/seed.json; legs are BSC Ondo contracts once validated."""
import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "pilots" / "seed.json"

PILOTS = {
    "pelosi-style": {
        "name": "pelosi-style",
        "label": "Pelosi-style",
        "tagline": "follows recent congressional disclosure buys",
        "disclaimer": "from public STOCK Act disclosures, delayed 30-45 days by law. not her trades, not advice.",
    },
    "buffett-style": {
        "name": "buffett-style",
        "label": "Buffett-style",
        "tagline": "steady names from 13f filings and the buffett-portfolio filter",
        "disclaimer": "from public 13f filings, delayed 45 days after quarter-end. not berkshire, not advice.",
    },
    "ai-chips": {
        "name": "ai-chips",
        "label": "AI chips",
        "tagline": "thematic basket of ai-chip stocks",
        "disclaimer": "thematic model portfolio. not advice.",
    },
}

ALIASES = {
    "pelosi": "pelosi-style",
    "nancy": "pelosi-style",
    "buffett": "buffett-style",
    "buffet": "buffett-style",
    "berkshire": "buffett-style",
    "chips": "ai-chips",
    "ai": "ai-chips",
    "ai-chips": "ai-chips",
    "semis": "ai-chips",
}


def load_seed() -> dict:
    try:
        return json.loads(SEED_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def find_pilot(text: str) -> str | None:
    t = text.strip().lower()
    for alias, pid in ALIASES.items():
        if alias in t:
            return pid
    return None


def legs_for(pilot_id: str) -> list[dict]:
    seed = load_seed()
    node = seed.get(pilot_id, {})
    return node.get("legs", []) or []


def watchlist_for(pilot_id: str) -> list[str]:
    seed = load_seed()
    node = seed.get(pilot_id, {})
    wl = node.get("watchlist") or (seed.get("watchlists", {}).get(pilot_id)) or []
    return wl


def intro_text() -> str:
    return (
        "hey, i'm pool. i help you copy investor-style portfolios in tokenized stocks on bnb chain. "
        "three to pick from: pelosi-style (from public disclosures, delayed), "
        "buffett-style (from 13f filings, delayed), and ai-chips. "
        "which one do you want?"
    )


def explain_text(pilot_id: str) -> str:
    p = PILOTS[pilot_id]
    legs = legs_for(pilot_id)
    if legs:
        tickers = ", ".join(l.get("ticker", "?") for l in legs)
        return f"{p['label']}: {p['tagline']} — right now {tickers}. {p['disclaimer']}"
    wl = watchlist_for(pilot_id)
    tickers = ", ".join(wl) if wl else "tbd"
    return (
        f"{p['label']}: {p['tagline']} — watching {tickers}, contracts still validating. "
        f"{p['disclaimer']}"
    )
