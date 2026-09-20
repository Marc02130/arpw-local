# AI Research Paper Writer (local)

A functional copy of sibling repo `../arpw` for a single researcher: upload three kinds of source (original research, style examples, and supporting reference papers), retrieve and pin passages, interrogate that corpus (supporting papers by default), optionally outline, then generate a section-by-section literature-backed draft. Citations must map to uploaded, pinned, or retrieved passages. It is not a paper mill.

This repo rebuilds that product on the **RAGged local stack**: Docker Compose, FastAPI, Webpack React, Postgres/pgvector, named volumes, cookie JWT, local MiniLM embeddings. There is no Vite Compose path and no Supabase runtime.

Spec: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Slice order: [`docs/PLAN.md`](docs/PLAN.md).

## In this README

| Kind | Where |
|---|---|
| Spec | [Architecture](docs/ARCHITECTURE.md), [plan](docs/PLAN.md), [docs index](docs/README.md), [product requirements](docs/PRODUCT_REQUIREMENTS.md) |
| Tutorial | [Get to the dashboard](#tutorial-get-to-the-dashboard) |
| How-to | [Confirm email](#how-to-confirm-email), [upload](#how-to-upload-sources), [chat key](#how-to-save-a-chat-key), [generate](#how-to-generate-a-draft), [tests](#how-to-run-tests) |
| Reference | [Ports and env](#ports-and-env), [routes](#routes) |
| Explanation | [Why three sources](#why-three-sources-and-why-interrogate-prefers-supporting-papers), [why this stack](#why-this-stack), [why email confirmation](#why-email-confirmation), [why chat keys are not shown on Profile](#why-chat-keys-are-not-shown-on-profile) |

## Tutorial: get to the dashboard

### What you'll need

- Docker
- An xAI / OpenAI / Anthropic API key only when you generate, outline, or interrogate (uploads embed on-server with MiniLM)

### Step 1: Start the stack

```bash
cp .env.example .env
# set JWT_SECRET (≥ 32 characters)
docker compose up --build
```

Open **http://localhost:8082/**. Health: `GET http://localhost:8082/api/health` → `{"status":"ok"}`.

### Step 2: Sign up and confirm

1. Create an account (password at least 6 characters).
2. Open Mailpit at [http://localhost:8026](http://localhost:8026).
3. Follow the confirm link. You land on sign-in; then the dashboard.

Do not mix `localhost` and `127.0.0.1` for confirm links **or** CSRF `Origin` headers. Compose `PUBLIC_ORIGINS` allowlists `http://localhost:8082` (and `:3001`), not `http://127.0.0.1:8082`. Use `http://localhost:8082` consistently.

### What you will have

A confirmed user, an `arpw_session` cookie, and `/dashboard`, `/generate/:id`, `/library`, and `/profile`.

## How-to: confirm email

Register, open [http://localhost:8026](http://localhost:8026), follow the confirm link. Resend from `/verify-email` if needed. Confirm links use `PUBLIC_APP_URL` (`http://localhost:8082`).

## How-to: upload sources

On the dashboard, drop pdf/docx/txt (≤10 MB). At most **10 files per drop**. Library totals: literature 500, original research 100, style examples 10. Status `Indexed (N chunks)` means MiniLM ingest finished.

## How-to: save a chat key

Profile → paste OpenAI, xAI (`xai-…`), and/or Anthropic keys → Chat with. The SPA never shows the secret again, only last4. Interrogate, outline, and generate use the selected provider.

## How-to: generate a draft

Start a paper (type dropdown), enter a research prompt, Query sources, optionally pin, optionally Interrogate, Generate outline, Generate draft. Open Library to continue, export Markdown/Word, or edit source citations.

## How-to: run tests

```bash
python3 -m venv api/.venv
source api/.venv/bin/activate
pip install -r api/requirements-dev.txt
pytest                 # unit
pytest -m uat          # Compose
pytest -m dogfood      # live walkthrough (skips without operator flag)
cd web && npm test     # Jest
SMOKE_BASE_URL=http://localhost:8082 ./scripts/smoke.sh
# health → confirm → upload → retrieve (exit 2 without xai- key)
DOGFOOD_BASE_URL=http://localhost:8082 ./scripts/dogfood.sh
# live key required: retrieve → pin → interrogate → outline → generate
```

Scripts default `DOGFOOD_BASE_URL` / `SMOKE_BASE_URL` to `http://127.0.0.1:8082`. That host is **not** in `PUBLIC_ORIGINS`. `dogfood.py` sends `Origin` equal to the base URL, so Settings PUT then returns **403 Invalid origin**. Override to **`http://localhost:8082`** unless you also list the `127.0.0.1` origin in `PUBLIC_ORIGINS`.

Literature-review UAT: [`UAT/README.md`](UAT/README.md). Waits are **not** ARPW’s 180s/300s. Run against **`:8082`**, not webpack `:3001`.

## Ports and env

| What | Where |
|---|---|
| App (nginx → SPA + `/api`) | `http://localhost:8082/` (RAGged keeps `:8080`) |
| Mailpit UI | `http://localhost:8026/` |
| Mailpit SMTP | container `mail:1025` (not published on the host) |
| Dev overlay API (optional) | host `:8002` + webpack `:3001` — dogfood generate on **:8082**, not :3001 |

Compose builds `DATABASE_URL` from `POSTGRES_*`. Do not set `DATABASE_URL` or `VITE_*`.

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database; Compose interpolates these into `DATABASE_URL` |
| `JWT_SECRET` | ≥ 32 characters; also wraps Fernet for pasted LLM keys |
| `COOKIE_SECURE` | `false` on HTTP |
| `PUBLIC_ORIGINS` | CSRF Origin allowlist (`http://localhost:8082,http://localhost:3001`) |
| `PUBLIC_APP_URL` | Confirm/reset link base (`http://localhost:8082`) |
| `EMBEDDING_PROVIDER` | `local` (default) or `stub` (tests). Stored model id is always `sentence-transformers/all-MiniLM-L6-v2` |

There are **no** chat API keys in `.env`. Paste OpenAI, xAI, and/or Anthropic keys on Profile. Interrogate, outline, and generate all use the same selected Chat provider.

## Routes

Target SPA routes (ARPW screens, not RAGged threads):

| Path | Screen |
|---|---|
| `/login` | Sign in / sign up |
| `/verify-email` | Confirm email |
| `/forgot-password` / `/reset-password` | Reset (`?token=` on the reset page) |
| `/dashboard` | Paper counts; start or continue |
| `/generate/:id` | Prompt tab: research prompt, section checkboxes, type/style/format dropdowns, query sources, outline, generate |
| `/generate/:id/interrogate` | Grounded Q&A; pin literature/primary |
| `/profile` | Display name; OpenAI / xAI / Anthropic keys (last4) + chat provider |
| `/library` | Drafts, citations, export |

## Why three sources, and why Interrogate prefers supporting papers

| Upload | What it is | Generate | Interrogate |
|---|---|---|---|
| Original research | Your work on this paper’s topic (`primary`) | Methods/Results (and Abstract/Intro unless Literature Review) | Optional; off by default |
| Style examples | Your own papers for voice | Tone/structure prefix only; never draft `[S#]` | Optional; off by default (Q&A only, not pinable) |
| Supporting papers | Published work to cite (`literature`) | Citations; pins-first retrieve | **On by default**; 16 of 20 slots when included |

You already know your own papers and this-study notes. Interrogate is for asking the supporting literature. You can still tick original research or style examples on a question. ARPW’s default was “literature and original research”; arpw-local defaults to literature and does not mix the three equally.

## Why this stack

ARPW today is Vite + local Supabase (GoTrue, PostgREST, Storage, Deno Edge). That is fragile for a single-machine rewrite (`supabase start`, Storage image tags, hash-384 ingest when no Grok key). RAGged already runs the same class of app as Compose + FastAPI + Webpack + pgvector with local MiniLM. arpw-local copies **ARPW’s product** onto **RAGged’s mechanics**. It does not import RAGged’s thread-centric chat UI.

## Why email confirmation

AUTH-7 is P0 on the ARPW PRD. Register does not set a session cookie. Login of an unconfirmed address returns `email_not_confirmed` and the verify screen. Local mail is Mailpit, not Supabase Inbucket.

## Why chat keys are not shown on Profile

The SPA must not be able to read keys back. Profile shows `{configured, last4}` per provider from `GET /api/settings/llm` (OpenAI, xAI, Anthropic) and a **Chat provider** dropdown. Generate, outline, and interrogate decrypt the **user row** on the API. There is no HTTP decrypt route and no env-file key.

## Docs

| File | Role |
|---|---|
| [docs/README.md](docs/README.md) | Spec index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Canonical implementation spec |
| [docs/PLAN.md](docs/PLAN.md) | Slice order (PR 01–12) |
| [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) | Requirement IDs (intent, not as-built) |
