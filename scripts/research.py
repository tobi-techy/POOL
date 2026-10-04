"""Research worker (stub -> live midweek). Drafts the rebalance note a pilot owner approves.

Reads: pilots/seed.json watchlists. Checks (manual until keyed): STOCK Act
disclosures, 13F filings, Binance RWA sector filters, tokenized-stock news.
Writes: docs/research-note-<date>.md with sources, diffs vs current weights,
and a proposed allocation the owner approves before any strategy publish.
The chat agent only ever suggests from an approved note. It never trades.
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    seed = json.loads((ROOT / "pilots" / "seed.json").read_text())
    today = datetime.date.today().isoformat()
    out = ROOT / "docs" / f"research-note-{today}.md"
    lines = [f"# Research note {today}", "",
             "Pilot diffs to check (sources: STOCK Act disclosures, 13F filings, RWA sector filters):", ""]
    for pid in ("pelosi-style", "buffett-style", "ai-chips"):
        node = seed.get(pid, {})
        wl = node.get("watchlist") or (seed.get("watchlists", {}).get(pid)) or []
        legs = [l.get("ticker") for l in node.get("legs", [])]
        lines.append(f"- {pid}: legs {legs or 'none validated'} / watching {wl}")
        lines.append("  sources checked: _none yet — fill before publish_")
        lines.append("  proposed change: _none_")
    lines += ["", "Rule: no strategy version is published from an unchecked box."]
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
