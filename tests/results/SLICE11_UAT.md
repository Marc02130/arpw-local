# arpw-local — UAT / dogfood results (slice11-docs-uat)

- **Repo:** [arpw-local](https://github.com/Marc02130/arpw-local) (not Marc02130/arpw)
- **Branch:** `slice11-docs-uat` @ `bf55878`
- **Date:** 2026-09-19 (America/New_York)
- **Checkout:** `/Users/marcbreneiser/Code/arpw-local/`
- **Gate:** **PASS** (pytest UAT + pytest dogfood health). Full `./scripts/dogfood.sh` deferred — no live xAI key (`DOGFOOD_XAI_KEY` / `UAT/.uat-grok-key`).

## Commands

```bash
cd /Users/marcbreneiser/Code/arpw-local
git checkout slice11-docs-uat
export ARPW_KEEP_COMPOSE=1
./api/.venv/bin/python -m pytest tests/uat -m uat -v --tb=short
ARPW_DOGFOOD=1 ./api/.venv/bin/python -m pytest tests/dogfood -m dogfood -o addopts= -v --tb=short
# Full operator walk (needs key):
# DOGFOOD_XAI_KEY=xai-... ./scripts/dogfood.sh
```

## UAT (Ragged QA, Mac)

- Full `tests/uat`: **16 passed** (~8.4s)
- Compose healthy on **`:8082`** (`arpw-local-api-1` healthy)
- Coverage: slices **01–09** (`test_uat_slice01` … `test_uat_slice09`)
- No pytest UAT modules yet for slice10 library / slice11 docs (unit + scripts cover those)

## Dogfood (Ragged Dogfood, Mac)

- `ARPW_DOGFOOD=1 pytest -m dogfood -o addopts=`: **1 passed** (`test_health_on_8082`)
- `./scripts/dogfood.sh`: **exit 2** — no live key; signup→generate walk not executed
- Live UI peek: SPA “AI Research Paper Writer” on `/`; Sign in/up, API key, Upload, Papers, Interrogate, Generate, Library present

## Open / Low (non-blocking)

1. Full operator dogfood gated on xAI key (by design; clear exit 2) — re-run when key available
2. Bundle has almost no `aria-` / `sr-only` (a11y polish later)
3. Docs port drift `:8080` vs Compose `:8082` — Ragged Documentarian syncing

## Severity

- Product bugs from this gate: **none**
- Low UX / env notes only

## Re-run (2026-09-19 ~20:46 ET)

- **UAT (Ragged QA, Mac):** `pytest tests/uat -m uat` — **16 passed** (~10.1s); Compose still healthy on `:8082`
- **Unit (spot):** `pytest tests/unit -m unit` — **71 passed** (~16s)
- **Dogfood pytest:** `ARPW_DOGFOOD=1 pytest -m dogfood -o addopts=` — **1 passed** (`test_health_on_8082`)
- **`./scripts/dogfood.sh`:** still blocked — `UAT/.uat-grok-key` exists but is **0 bytes**; no `DOGFOOD_XAI_KEY` in env/.env
- **Gate:** remains **PASS** (pytest UAT + dogfood health). Full operator walk still deferred pending a live `xai-` key

