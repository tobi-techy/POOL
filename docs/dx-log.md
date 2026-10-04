# POOL — friction log (this is 25% of the score, write it like a human)

Rule: every external call gets one row. URL, status, latency, one sentence on what confused you.
Do not polish. Specific beats polite.

| date UTC | system | endpoint | status | latency | note |
| --- | --- | --- | --- | --- | --- |
| 2026-10-04 | scaffold | local python compile + seed fetch | | | first rows tonight |
| 2026-10-04 | binance-rwa | GET bapi …/rwa/stock/detail/list/ai?type=1 (httpx, 20s) | ConnectTimeout | 30000 | www.binance.com unreachable from dev machine; web3.binance.com also failed DNS earlier. Docs + Glider fetch fine, so machine network is up — looks Binance-specific. Fallback seed.json written with watchlists only; retry on other network + log. First real finding for the DX report. |
| 2026-10-04 | agent | reply() smoke (hi / copy / portfolio / news) | ok | — | conversational stubs respond; DB event log writes. |
