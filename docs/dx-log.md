# POOL — friction log (this is 25% of the score, write it like a human)

Rule: every external call gets one row. URL, status, latency, one sentence on what confused you.
Do not polish. Specific beats polite.

| date UTC | system | endpoint | status | latency | note |
| --- | --- | --- | --- | --- | --- |
| 2026-10-04 | scaffold | local python compile + seed fetch | | | first rows tonight |
| 2026-10-04 | binance-rwa | GET bapi …/rwa/stock/detail/list/ai?type=1 (httpx, 20s) | ConnectTimeout | 30000 | www.binance.com unreachable from dev machine; web3.binance.com also failed DNS earlier. Docs + Glider fetch fine, so machine network is up — looks Binance-specific. Fallback seed.json written with watchlists only; retry on other network + log. First real finding for the DX report. |
| 2026-10-04 | agent | reply() smoke (hi / copy / portfolio / news) | ok | — | conversational stubs respond; DB event log writes. |
| 2026-10-04 | photon-docs | connection-and-routing (Stable) | ok | — | sidecar send was wrong (`app.imessage` / `im.space(phone)` don't exist). Correct: `imessage(app).user(phone)` → `im.space.create(user)` → `space.send`; inbound via `imessage(space)`/`imessage(message).sender`, cache live spaces. Quotas noted: 5k msgs/server/day, 50 new convos/line/day. Fixed in v0.2. |
| 2026-10-04 | glider-docs | two-stage enrollment (local llms-full) | ok | — | stage1 `POST /enroll/signature {ownerAccountId eip155:0:.., strategyId, chainIds:[56], accountType:ECDSA}` → sign `message.raw` → stage2 echoes all fields byte-for-byte + signature + portfolioName. flowId = idempotency anchor, 24h. Chain 56 support is per-tenant — day-one `whoami` + stage1 check. Built into copyengine.py. |
| 2026-10-04 | dialogue | smoke_journey (hey→pelosi→twenty bucks→YES→status→cash out) | ok | — | found + fixed: word-amounts ("twenty") parsed; YES-after-unavailable-quote now waitlists instead of re-asking amount. Quote timeout cut 20s→12s for chat latency. |
