# POOL

Text-message copy trading of investor-style tokenized-stock baskets on BSC. iMessage in, Glider copy engine, Binance Web3 data under it.

## Tonight (no keys needed)

```bash
/opt/homebrew/bin/python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --port 8000   # http://127.0.0.1:8000/health
python scripts/seed_pilots.py                # writes pilots/seed.json from the live Ondo/BSC list
```

Sidecar (needs Photon project id + secret):

```bash
cd sidecar && npm install && npm start
```

Text the Photon line. Python replies through the sidecar. Tonight she shows pilots and live prices; copying goes live Wednesday.

## Judge path

1. Text the number in the submission. Say hi.
2. Pick a pilot in words ("pelosi one, twenty bucks").
3. She quotes on-chain vs reference price, names the spread guard result, asks for yes.
4. Yes enrolls the demo wallet and starts the copy. Status anytime.

Pilots are model portfolios from delayed public filings, not live brokerage. She is not an investment advisor.

## Layout

- `app/` python brain (fastapi, tools, conversational replies)
- `sidecar/` only process that touches Photon (`spectrum-ts`)
- `pilots/seed.json` generated weights (BSC Ondo only)
- `docs/TECHNICAL_REQUIREMENTS.md` the build spec
- `docs/dx-log.md` friction log — every external call gets a row
