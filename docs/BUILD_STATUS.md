# POOL — Build Status & Gap Analysis

Reviewed 2026-10-04 against `docs/TECHNICAL_REQUIREMENTS.md` (the spec). Submission lock: Sun 11 Oct 2026, 12:00 UTC.

**One-line verdict:** the conversational shell, data model, sidecar pipe, and Glider enroll/start/rebalance client are real and run offline. Everything that touches live money — Binance quote/simulate, the spread guard, Glider strategy creation, enrollment signing, funding, and the LLM voice — is stubbed, blocked on missing API keys, or blocked on the dev machine's inability to reach www.binance.com. The demo today is an honest "prices aren't loading" refusal, not a fill.

---

## 1. What is built and verified working

Run `python scripts/smoke_journey.py` — passes end to end with no network.

- **Agent HTTP surface** (`app/main.py`): `POST /internal/inbound`, `POST /hooks/spectrum` (Photon webhook fallback), `GET /health`, `GET /debug/pilots`. Sidecar-secret auth on inbound. Errors are caught so the user always gets a reply.
- **Conversation state machine** (`app/dialogue.py`): `new → browsing → picked → confirm_pending → running`. Keyword routing, word-amount parsing ("twenty bucks" → 20), YES/NO handling, per-user stage persisted in SQLite.
- **Confirm-token gate** (`app/quote.py`): `arm_confirm` / `take_confirm`, single-use, 10-min TTL, bound to phone + pilot + notional + quote id. "yes" does nothing without a pending quote. This is the spec's core safety rule and it is real.
- **Pilot catalog** (`app/pilots.py`): 3 pilots (pelosi-style, buffett-style, ai-chips) with aliases, honest disclaimers ("not her trades, not advice"), seed loading.
- **Data model** (`app/db.py`): 5 tables — `pilots`, `users`, `copies`, `events`, `confirms` — plus additive migrations. Positions are correctly read live, not stored.
- **Glider copy client** (`app/copyengine.py`): `whoami`, `begin_enrollment` (stage-1 `/enroll/signature`), `complete_enrollment` (stage-2 byte-for-byte echo + signature + flowId), `start_and_rebalance`, `poll_operation` (2–5s poll to terminal status), `positions`, `record_copy`. Matches the two-stage signed-enrollment contract in the dx-log.
- **Binance read layer** (`app/tools/binance.py`): public RWA list (`type=1` Ondo), filtered to `chainId=56`. No key needed.
- **iMessage sidecar** (`sidecar/src/index.js`, ~100 lines): `spectrum-ts` + `imessage` provider. Inbound stream → normalized JSON → Python; `POST /send` outbound via `imessage(app).user(phone)` → `space.create` → `space.send`. Message-id dedupe, live-space cache. Correct per the dx-log's routing fix.
- **DX friction log** (`docs/dx-log.md`): 6 honest rows including a real ConnectTimeout finding and the Photon send-API correction.
- **Safety caps** (`app/config.py`): $25/copy, $100 total, hardcoded.

---

## 2. Partially built / degraded

- **Quote path** (`app/quote.py:build_quote`): fetches the RWA list and builds `Leg` objects, but the legs carry no prices. The `Leg` dataclass has `onchain_price`, `ref_price`, `spread_bps`, `pause_reason`, and `Quote` has `market_open` / `needs_second_confirm` — **none of these are ever populated**. When Binance is reachable it will produce a leg list with contract addresses but no observed prices, so `ok` stays effectively unusable for a real confirm.
- **Copy start** (`app/copyengine.py:start_copy_texts`): with no `GLIDER_API_KEY` it records the copy as `quoted` and texts "enrollment opens wednesday". Honest, but it is a waitlist, not a copy.
- **Status** (`app/dialogue.py:_status`): returns canned text from the `copies` table. Does not call Glider `/positions` or the Binance Wallet API.
- **Research worker** (`scripts/research.py`): writes a template note with `_none yet_` placeholders. No STOCK Act, 13F, or news ingestion.
- **Pilot seed** (`pilots/seed.json`): **empty legs** — fallback watchlists only. `scripts/seed_pilots.py` exists but cannot run because www.binance.com times out from this machine (dx-log row 2). No validated BSC contracts today.

---

## 3. Not built (spec gap list)

| Spec requirement | Status |
| --- | --- |
| **LLM voice / tool-calling agent** (spec §3, §5) | Not built. `app/agent.py` is a pass-through to the state machine. `llm_enabled()` exists but there is no LLM client, no tool loop, no system prompt. It is a keyword router, not "one LLM agent with tool access." |
| **Spread guard** (spec §4, the creativity differentiator) | Not implemented. No market-status read, no on-chain-vs-reference comparison, no 150 bps threshold check, no second-confirm, no paused-leg dropping. The guard logic is absent; only the data fields exist. |
| **Binance Trading quote + Transaction simulate + Wallet API** (spec §6, required modules) | Not built. `binance_api_key`/`binance_api_secret` are in config but used nowhere. `binance-web3-wallet` is in `requirements.txt` but never imported. Only the keyless public RWA list is called — so the "three Binance modules" scoring surface is currently one. |
| **Glider strategy create/publish + version bump + discovery** (spec §6) | Not built. No `POST /strategies`, no publish, no `/discovery/strategies`. Enroll/start/rebalance exist; strategy lifecycle does not. |
| **Enrollment signing page** (spec §6: "iMessage can't sign EIP-712") | Not built. `begin_enrollment` returns the signable message but no UI lets a user sign it. |
| **DirectSwapAdapter** (fallback fill, spec §4) | Not built. |
| **Funding** (USDT transfer to smart account) | Not built. |
| **Withdraw flow** | Dialogue promises it ("say the word and I'll prepare it"); nothing prepares a `/withdraw/signature`. |
| **Pause/resume** | Dialogue returns canned "paused" text; no actual automation pause call. |
| **Deployment** (public HTTPS VM up through 23 Oct) | Not built. Laptop-only. |

---

## 4. Code issues found

- **`app/copyengine.py:90` — `time.sleep(every_s)` inside `async def poll_operation`.** Blocks the event loop for up to 2 min (30 tries × 4s). Should be `await asyncio.sleep(every_s)`.
- **`app/main.py:20-28` — synchronous `urllib.request` inside the async `/internal/inbound` handler.** Blocks the loop on every reply. Should use `httpx.AsyncClient` (already a dependency).
- **`app/main.py:15` — `@app.on_event("startup")` is deprecated** in current FastAPI; use a lifespan context manager.
- **`app/tools/glider.py` is dead code** — `copyengine.py` makes its own httpx calls and never imports it.
- **`app/dialogue.py:50-54` — redundant branch**: both arms of `if u["stage"] == "picked" and u["picked_pilot"] == pid` return identical text.
- **`app/quote.py:confirm_text`** references `q.market_open` and `q.needs_second_confirm`, which are never set — the second-confirm guard path is unreachable.
- **No test suite** beyond `smoke_journey.py`.

---

## 5. Hackathon scoring impact

- **Technical implementation (30%)** — at risk. Live mainnet path is not running: no Binance key calls, no Glider key calls, no simulate, untested operation polling. Only the keyless RWA list fires.
- **Creativity (25%)** — at risk. The headline feature (closed-market spread guard) is not implemented.
- **DX Report (25%)** — on track but thin. 6 honest rows; needs latency tables and the Ondo-on-BSC behavior findings once the key/network path works.
- **Product quality (20%)** — strong. Offline dialogue is clean, honest, plain-English, and refuses to invent prices.

---

## 6. Critical path to a scorable demo (priority order)

1. **Fix network egress to www.binance.com / web3.binance.com** (or run from the hackathon VM). Nothing live works until the RWA list, Trading quote, and Transaction simulate are reachable. This blocked seed generation on 10-04.
2. **Obtain and wire the Binance Web3 key** — Trading quote + Transaction simulate + Wallet API. This is 2 of the 3 required modules and the entire quote/spread-guard input.
3. **Implement the spread guard** in `build_quote`: market status, per-leg on-chain vs reference (divide by `multiplier`), 150 bps threshold, second-confirm, paused-leg drop. This is the creativity score.
4. **Obtain the Glider B2B key**, run `whoami` + stage-1 enroll as the day-one chain-56 tenant check, then `POST /strategies` for the three pilots.
5. **Build the enrollment signing page** (EIP-712 sign for the demo owner) so `complete_enrollment` can actually run.
6. **Replace `agent.py` with the tool-calling LLM** (or document the state machine as the intended "voice" and ship it — a correct refusal still demos well).
7. **Fix the two event-loop blockers** (`time.sleep`, sync `urllib`) before any live polling.
8. **Seed real legs** via `scripts/seed_pilots.py` once Binance is reachable.
9. **Deploy to a public HTTPS VM** and keep it up through 23 Oct.

---

## 7. Notes

- The codebase is honest by design: degraded paths refuse rather than fake. That is the right instinct for the "a correct refuse-to-trade is a better demo than a lucky fill" rule, but a demo that only refuses needs at least one real fill on mainnet to hit the technical bar (spec §12, item 3).
- Eligibility gate (spec §2: not open to US/CA/NL/UK/JP/IR/CU/KP/CR/DN/LU residents) must be confirmed before any account creation — the spec flags it, the code does not enforce it.
