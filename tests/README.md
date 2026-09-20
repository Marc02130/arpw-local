# Tests

| Command | What |
|---|---|
| `pytest` | Fast unit (default `-m unit`). No Compose. `EMBEDDING_PROVIDER=stub`. |
| `pytest -m uat` | Compose stack on `:8082`. |
| `pytest -m dogfood` | Live walkthrough; skip unless `ARPW_DOGFOOD=1`. |
| `cd web && npm test` | Jest (`validateAuth`, `exportPaper`). |
| `./scripts/smoke.sh` | health → register → Mailpit confirm → login → paper → upload nfr7 → retrieve. Exit 2 without a live `xai-` key. |
| `./scripts/dogfood.sh` | Operator walkthrough on `:8082`: key → upload → retrieve → pin → interrogate → outline → generate → library. Needs `DOGFOOD_XAI_KEY` or `UAT/.uat-grok-key`. |
| `node UAT/run-literature-review.mjs` | Playwright vs `:8082` (not webpack `:3001`). Upload wait `ceil(n/10)*120s+60s`. See [`UAT/README.md`](../UAT/README.md). |

Markers: `unit`, `uat`, `dogfood`, `slice01`…`slice12`.

Point-in-time gate notes: [`results/README.md`](results/README.md) ([`results/SLICE11_UAT.md`](results/SLICE11_UAT.md)).
