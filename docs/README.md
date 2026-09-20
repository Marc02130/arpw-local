# DOCUMENTS

Index of product and engineering specs for **arpw-local**: a functional copy of ARPW on the RAGged local stack (Compose, FastAPI, Webpack React, Postgres/pgvector). No Supabase runtime.

The user-facing walkthrough is [`../README.md`](../README.md). Do not treat README feature rows as the PRD. Prefer live RAGged code and that repo’s current README/guides over any older markdown tree.

## Content

| File | Role | What it is |
|---|---|---|
| [../README.md](../README.md) | Tutorial / how-to / reference / explanation | First run, confirm email (Mailpit `:8026`), upload, Profile chat keys, tests, ports, routes, why |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Implementation spec | Stack, auth, ingest, retrieve, generate, parity matrix. Canonical as slices land |
| [PLAN.md](./PLAN.md) | Slice order | PR 01–12, dependencies. Not behavior. Status: slices 01–11 on `slice11-docs-uat`; PR 12 not started |
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) | Intent | ARPW requirement IDs (AUTH, DOCS, GEN, INT, PIN, QUAL, LIB, NFR). Stack sentences point here; Keep/Adapt/Drop is in ARCHITECTURE |
| `TECHNICAL_SPECIFICATION.md` | As-built (placeholder) | Not written yet. Schema, APIs, ingest, and generate as-built live in code plus [ARCHITECTURE.md](./ARCHITECTURE.md) until this file exists |
| `GENERATION_SLICES.md` / `OUTLINE_SLICES.md` / `INTERROGATION_SLICES.md` | Historical product intent | Ported from ARPW; status = port. Not written until those PRs |
| [../UAT/README.md](../UAT/README.md) | UAT / dogfood | Literature-review playbook against `:8082`. Do not copy ARPW’s 180s/300s waits as constants (`ceil(n/10)*120s+60s` upload; generate 1260s) |
| [../tests/README.md](../tests/README.md) | Tests | pytest unit/uat/dogfood + Jest + [`../scripts/smoke.sh`](../scripts/smoke.sh) + [`../scripts/dogfood.sh`](../scripts/dogfood.sh) + UAT runner |
| [../tests/results/README.md](../tests/results/README.md) | Gate evidence | Point-in-time UAT/dogfood notes (not live) |

**Which file to open**

- What we are building and how: [ARCHITECTURE.md](./ARCHITECTURE.md)
- What to implement next: [PLAN.md](./PLAN.md)
- Requirement IDs / MVP cut: [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)
- First run (Compose): [`../README.md`](../README.md)

**Test entry points**

- Unit / Compose UAT / live pytest dogfood: [`../tests/README.md`](../tests/README.md)
- Smoke: [`../scripts/smoke.sh`](../scripts/smoke.sh)
- Operator dogfood (live `xai-` key): [`../scripts/dogfood.sh`](../scripts/dogfood.sh)
- Literature-review UAT: [`../UAT/README.md`](../UAT/README.md)
- Latest recorded gate: [`../tests/results/SLICE11_UAT.md`](../tests/results/SLICE11_UAT.md)

## References

- Product source: `~/Code/arpw` (`.docs/`, `src/`, `supabase/`)
- Stack source: `~/Code/ragged` (`docker-compose.yml`, `api/`, `web/`, current README/guides)
