# Tests

| Command | What |
|---|---|
| `pytest` | Fast unit (default `-m unit`). No Compose. `EMBEDDING_PROVIDER=stub`. |
| `pytest -m uat` | Compose stack on `:8082`. |
| `pytest -m dogfood` | Live walkthrough; skip unless `ARPW_DOGFOOD=1`. |
| `cd web && npm test` | Jest (`validateAuth`, `exportPaper`). |
| `./scripts/smoke.sh` | health → register → Mailpit confirm → login → paper → upload nfr7 → retrieve. Exit 2 without a live `xai-` key. |
| `node UAT/run-literature-review.mjs` | Playwright vs `:8082`. See [`UAT/README.md`](../UAT/README.md). |

Markers: `unit`, `uat`, `dogfood`, `slice01`…`slice12`.
