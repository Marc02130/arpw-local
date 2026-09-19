# DOCUMENTS

Index of product and engineering specs for **arpw-local**: a functional copy of ARPW on the RAGged local stack (Compose, FastAPI, Webpack React, Postgres/pgvector). No Supabase runtime.

The user-facing walkthrough will live in [`../README.md`](../README.md). Do not treat README feature rows as the PRD. Do not copy `ragged/documents/*.md` (those still describe a Supabase Edge stack).

## Content

| File | Role | What it is |
|---|---|---|
| [../README.md](../README.md) | Tutorial / how-to / reference / explanation | First run, confirm email (Mailpit `:8025`), upload, Profile chat keys, tests, ports, routes, why |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Implementation spec | Stack, auth, ingest, retrieve, generate, parity matrix. Canonical until slices land |
| [PLAN.md](./PLAN.md) | Slice order | PR 01–12, dependencies. Not behavior |
| [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) | Intent | ARPW requirement IDs (AUTH, DOCS, GEN, INT, PIN, QUAL, LIB, NFR). Stack sentences point here; Keep/Adapt/Drop is in ARCHITECTURE |
| `TECHNICAL_SPECIFICATION.md` | As-built | Filled in during implementation (schema, APIs, ingest, generate as they land) |
| `GENERATION_SLICES.md` / `OUTLINE_SLICES.md` / `INTERROGATION_SLICES.md` | Historical product intent | Ported from ARPW; status = port. Not written until those PRs |
| `../UAT/README.md` | UAT / dogfood | Literature-review playbook against `:8080` (PR 11). Do not copy ARPW’s 180s/300s waits |
| `../tests/README.md` | Tests | pytest unit/uat/dogfood + Jest + smoke |

**Which file to open**

- What we are building and how: [ARCHITECTURE.md](./ARCHITECTURE.md)
- What to implement next: [PLAN.md](./PLAN.md)
- Requirement IDs / MVP cut: [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)
- First run (after Compose exists): `../README.md`

## References

- Product source: `~/Code/arpw` (`.docs/`, `src/`, `supabase/`)
- Stack source: `~/Code/ragged` (`docker-compose.yml`, `api/`, `web/`). Live code beats stale markdown under `ragged/documents/`
