# Tests

| Command | What |
|---|---|
| `pytest` | Fast unit (default `-m unit`). No Compose. `EMBEDDING_PROVIDER=stub`. |
| `pytest -m uat` | Compose stack on `:8082`. |
| `pytest -m dogfood` | Live walkthrough; skip unless `ARPW_DOGFOOD=1`. |
| `cd web && npm test` | Jest (`validateAuth`, `exportPaper`). |
| `SMOKE_BASE_URL=http://localhost:8082 ./scripts/smoke.sh` | health → register → Mailpit confirm → login → paper → upload nfr7 → retrieve. Exit 2 without a live `xai-` key. |
| `DOGFOOD_BASE_URL=http://localhost:8082 ./scripts/dogfood.sh` | Operator walkthrough on `:8082`: key → upload → retrieve → pin → interrogate → outline → generate → library. Needs `DOGFOOD_XAI_KEY` or `UAT/.uat-grok-key`. |
| `node UAT/run-literature-review.mjs` | Playwright vs `:8082` (not webpack `:3001`). Upload wait `ceil(n/10)*120s+60s`. See [`UAT/README.md`](../UAT/README.md). |

Operator scripts must use **`http://localhost:8082`**, not `http://127.0.0.1:8082`, unless `PUBLIC_ORIGINS` also lists the 127.0.0.1 origin. Compose `.env` allowlists `http://localhost:8082` and `http://localhost:3001` only. `dogfood.py` sends `Origin` matching `DOGFOOD_BASE_URL`; the 127.0.0.1 default then fails Settings PUT with **403 Invalid origin**.

Markers: `unit`, `uat`, `dogfood`, `slice01`…`slice12`.
