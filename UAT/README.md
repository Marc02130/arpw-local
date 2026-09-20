# Literature-review UAT

Dogfood arpw-local by drafting a **Literature Review** from PDFs in `UAT/papers/`. Humans and agents follow this playbook. The Playwright runner is `UAT/run-literature-review.mjs`.

This is not `pytest`. The unit suite never calls xAI. This UAT does: upload, index, retrieve, pin, interrogate, generate, preview, save, export. Local Compose only (`http://localhost:8082`).

Do **not** commit files under `UAT/papers/` (copyrighted PDFs), `UAT/reports/`, or `UAT/.uat-grok-key`.

## In this playbook

| Kind | Where |
|---|---|
| Tutorial | [Run the UAT](#tutorial-run-the-literature-review-uat) |
| How-to | [Stack](#how-to-bring-the-stack-up), [key fixture](#how-to-set-the-chat-key-fixture) |
| Reference | [Paper](#paper-to-start), [waits](#reference-waits), [fail](#fail-the-uat) |

Product walkthrough: [`../README.md`](../README.md). Spec: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Goal

Prove the grounded path on a real pile of papers. Fail if generate runs without a real `xai-` key, if a citation is not from the uploaded set, if indexing never shows chunks, if **References** is not an academic list, if Interrogate on an evidence question returns only bibliography chunks, or if Continue restores a paper type other than Literature Review.

Uncited-sentence ⚠ marks do not fail this UAT (QUAL-1 leftovers after one repair pass).

## Paper to start

- Title: `Gut-brain axis in Alzheimer’s disease: a literature review`
- Type: **Literature Review**
- Sections: Abstract, Introduction, Literature Review, Discussion, Conclusion, References (leave Methods and Results off)
- Citation style: APA
- Output: Markdown
- Research prompt:

> Synthesize a literature review of the gut-brain axis in Alzheimer’s disease from the uploaded papers only. Cover microbiome, inflammation, omega-3 fatty acids, and clinical-trial evidence. Cite only retrieved [S#] ids. Do not invent studies, n, or outcomes.

## Tutorial: run the literature-review UAT

### What you'll need

- Docker
- Node.js
- The literature PDFs in `UAT/papers/` (restore from the ARPW UAT corpus; do not download replacements here)
- A real xAI secret starting with `xai-` in `UAT/.uat-grok-key` (gitignored)

### Steps

```bash
cp .env.example .env
docker compose up --build
printf '%s' 'xai-...' > UAT/.uat-grok-key
cd UAT && npm install && npx playwright install chromium
node run-literature-review.mjs
```

App: [http://localhost:8082](http://localhost:8082). Mailpit: [http://localhost:8026](http://localhost:8026). Do not run this against webpack `:3001`. Operator scripts (`./scripts/dogfood.sh`, `./scripts/smoke.sh`) must set `DOGFOOD_BASE_URL` / `SMOKE_BASE_URL` to **`http://localhost:8082`** (not `127.0.0.1`) unless `PUBLIC_ORIGINS` also lists that origin — otherwise Settings PUT returns **403 Invalid origin**. **Harness-only:** `dogfood.py` UTF-8-decodes `export.docx` and can raise `UnicodeDecodeError` before checking status; product Word export is not implicated. See [`../tests/README.md`](../tests/README.md).

## How-to: bring the stack up

`docker compose up --build` until `GET http://localhost:8082/api/health` is `{"status":"ok"}`.

## How-to: set the chat key fixture

Put a single line `xai-...` in `UAT/.uat-grok-key`. Never a filesystem path. Never an env `XAI_API_KEY` in `.env`.

## Reference: waits

Do **not** copy ARPW’s 180s upload / 300s generate waits.

`UAT_UPLOAD_WAIT_MS(n) = ceil(n / 10) * 120000 + 60000`

That matches `web/src/components/UploadZone.tsx` (`DROP_LIMIT = 10`, `CONCURRENCY = 10`) and `UAT/run-literature-review.mjs`. The 180s/300s **upload** numbers below are that formula (one or two waves of 10), not ARPW’s copied 180s upload / 300s generate constants. Generate is **1_260_000 ms**.

| Site | Timeout |
|---|---|
| 10-file drop indexed | **180_000 ms** (`ceil(10/10)*120s+60s`) |
| 20 files indexed | **300_000 ms** (`ceil(20/10)*120s+60s`) |
| Outline | **180_000 ms** |
| Generate (five chat sections) | **1_260_000 ms** |

SPA in-flight upload concurrency is **10**. uvicorn still has 2 workers; extra POSTs queue in nginx.

## Fail the UAT

- Fewer than the expected PDFs in `UAT/papers/`
- Key fixture missing or not `xai-`
- A file never shows Indexed (N chunks)
- Generate without a live key
- Continue restores a type other than Literature Review
- Interrogate evidence answer is bibliography-only
- References list is filenames instead of citations
