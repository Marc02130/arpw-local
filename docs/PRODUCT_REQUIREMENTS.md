# PRODUCT_REQUIREMENTS

## Overview

Product requirements for **arpw-local**, a functional copy of AI Research Paper Writer (ARPW). This document states the intended MVP. It is not a status report. Requirement IDs are copied from ARPW `.docs/PRODUCT_REQUIREMENTS.md` v1.4. Keep / Adapt / Drop for this stack lives in [ARCHITECTURE.md](./ARCHITECTURE.md#feature-parity-matrix).

- Product: arpw-local (ARPW product, RAGged local stack)
- Audience: individual academic users (researchers, PIs, graduate students)
- Platform: web (desktop first)
- Version of this PRD: 1.4-local
- Date: 2026-09-19
- Status: current product intent for the rewrite
- Stack: Docker Compose, FastAPI, Webpack React, Postgres/pgvector — **not** Supabase Auth, PostgREST, Storage, or Deno Edge. Where a row below names Supabase, read the Adapt note in ARCHITECTURE.

For as-built vs target after slices land, see [ARCHITECTURE.md](./ARCHITECTURE.md). For what ARPW itself does today, see `~/Code/arpw/.docs/GAP_ANALYSIS.md`.

ARPW is a **grounded drafting assistant**. The researcher interrogates their own corpus, pins passages to include, then generates section drafts with citations that map to those passages (pins first, then retrieval). It requires human review before anything looks like a submission. It is not a paper mill and it must not emit citations that are not in the retrieved-or-pinned set.

## Content

### 1. Problem

Writing a literature-backed draft from a personal PDF pile is slow. Generic chat models invent citations. Researchers need a private corpus, retrieval they can inspect, and a draft they can edit.

### 2. Goals

**User goals**

- Upload three sources: original research (`primary`), optional style examples, and supporting reference papers (`literature`).
- Interrogate that corpus (defaults to supporting papers; original research and examples optional) and **pin** literature/primary chunks into the draft.
- Ask for a paper on a topic, pick sections and paper type, get a draft grounded in pins plus retrieved files.
- See which source passage supports each claim.
- Keep versions, export Markdown or Word, review before use.

**Product goals**

- Time-to-first-draft measured in minutes after the corpus is indexed, not hours of blank-page writing.
- Every generated citation traces to an uploaded file and chunk.
- Outputs carry a visible disclaimer: AI-generated draft, requires human review.

**Non-goals (MVP)**

- Multi-author collaboration or shared libraries.
- Mobile-first layout.
- Journal submission, plagiarism scanning, or publisher templates.
- Generating a full paper from 10–20 random chunks with no section-wise retrieval.
- User-editable system prompts or per-section prompt templates (server owns type × section templates).
- A separate Storage bucket for original research (same `"references"` table and cap; two upload sections).
- Merging Ragged (or any second RAG chat app) into this repo.
- Importing a chat transcript as literature or as a citable primary file. Interrogation chat is notes, never `[S#]` evidence.

### 3. Users

Primary: a single researcher with a folder of PDFs and an xAI Grok API key.

Assumptions: they will review the draft; they own the rights to upload the files; they use a laptop browser.

### 4. Functional requirements

Each item has an ID for the gap analysis.

#### AUTH

| ID | Requirement | Priority |
|---|---|---|
| AUTH-1 | Email/password sign up and sign in (FastAPI cookie JWT; no Supabase Auth). Signup is open; no invite list. | P0 |
| AUTH-2 | Session persist and restore; sign out. | P0 |
| AUTH-3 | Create `user_profile` on first signup (`user_id` = `auth.uid()`). | P0 |
| AUTH-4 | Profile page: edit full name. | P1 |
| AUTH-5 | Store OpenAI, xAI, and Anthropic API keys server-side, not as plaintext readable by the SPA. User picks `chat_provider`. | P0 |
| AUTH-6 | Invalid credentials show a clear error. | P0 |
| AUTH-7 | No app access until the email is confirmed (`email_confirmed_at`). Unverified users stay on a verify screen; they can resend the email. | P0 |
| AUTH-8 | Password reset: request a link by email, land on a reset page, set a new password. | P0 |

#### DOCS

| ID | Requirement | Priority |
|---|---|---|
| DOCS-1 | Upload references: PDF, DOCX, TXT; max 10 MB each; cap 500 files per user. | P0 |
| DOCS-2 | Upload style examples: same types; cap 10 files. | P1 |
| DOCS-3 | Drag-and-drop and file picker; progress per file. | P1 |
| DOCS-4 | List uploaded files (name, size, date) and delete (storage + metadata + vectors). | P0 |
| DOCS-5 | Parse text, chunk with section/page metadata, embed, store in `pgvector`. | P0 |
| DOCS-6 | Reject unsupported types and oversize files before upload. | P0 |
| DOCS-7 | Enforce the 500 / 10 caps against existing rows, not only the current batch. | P1 |
| DOCS-8 | Each reference has `source_role`: `literature` (default, published sources) or `primary` (the author’s original research on this paper’s topic). Upload UI may split those into two sections; same table, bucket, and cap as DOCS-1. The user can recategorize. Not used on example papers. | P0 |

#### GEN

| ID | Requirement | Priority |
|---|---|---|
| GEN-1 | Research prompt textarea (topic, question, constraints). Pins are structured includes, not free-text prompts. Interrogation chat is not generation text. **Section checkboxes:** Abstract, Introduction, Literature Review, Methods, Results, Discussion, Conclusion, References. | P0 |
| GEN-2 | **Paper Type dropdown:** Empirical Study, Literature Review, Theoretical Paper, Case Study. Type selects the server template pack. | P0 |
| GEN-3 | **Citation Style dropdown:** APA, MLA, Chicago (default APA). **Output Format dropdown:** Markdown, Word (default Markdown). | P1 |
| GEN-4 | Retrieve relevant reference chunks per section (hybrid search + rerank later); filter by `source_role` (see generation slices); **pins first**, then vector search; show sources in the UI. | P0 |
| GEN-5 | Generate **section by section**. Each section uses a frozen server template for that paper type × section, its own retrieval, and the research prompt. | P0 |
| GEN-6 | Citations only from retrieved `source_id`s; drop invented citations. | P0 |
| GEN-7 | Example papers constrain tone/structure only; they are not evidence. | P1 |
| GEN-8 | Outline mode: generate an editable outline, then full draft. | P2 |
| GEN-9 | Save draft to `user_papers` with config, version, status. Generate must not overwrite `paper_type`. Continue restores title, type, sections, and prompt. Each uploaded source stores a preformatted `citation_text` (fetched on upload from the DOI cite; editable on Library). References uses that string. | P0 |
| GEN-10 | Link cited files in `paper_references`. | P0 |

#### INT (interrogation)

| ID | Requirement | Priority |
|---|---|---|
| INT-1 | Interrogate tab on the current paper: ask a question of the uploaded sources; show retrieved passages; Grok answers using only those `[S#]` ids. **Default and ranking focus on supporting papers** (`literature`). Original research (`primary`) and style examples are optional includes — the researcher already knows those. | P0 |
| INT-2 | Interrogation uses the same embeddings and selected chat provider as generate. SPA never sees keys. Retrieve is academic-paper-tuned: drop bibliography and boilerplate unless the question asks for citations. Default corpus is literature; the user can add primary and/or examples per question. | P0 |
| INT-3 | Saved interrogation turns are notes. They must not be retrieved as evidence or numbered as `[S#]`. | P0 |

#### PIN

| ID | Requirement | Priority |
|---|---|---|
| PIN-1 | User can pin a retrieved chunk (`vector_id`, `file_id`) to the current paper, optionally with a target section. List and unpin. Own rows only. | P0 |
| PIN-2 | Generate’s allow-list is pinned chunks (for that section or unscoped) plus role-filtered retrieval. Example-paper pins are rejected. | P0 |

#### QUAL

| ID | Requirement | Priority |
|---|---|---|
| QUAL-1 | Attribution: each generated sentence maps to chunk id + quote span, or is flagged uncited. | P0 |
| QUAL-2 | Citation check: citations exist in retrieved set and `paper_references`. | P0 |
| QUAL-3 | Format check: required sections present. | P2 |
| QUAL-4 | Preview with inline warnings and footer disclaimer. | P0 |
| QUAL-5 | Do not treat cosine > 0.7 as “factual accuracy.” | P0 (constraint) |

#### LIB

| ID | Requirement | Priority |
|---|---|---|
| LIB-1 | Library table: title, type, status, date, version. Paginate 25 latest-title rows per page. Source citations paginate 25 per page. | P0 |
| LIB-2 | Version history grouped by title; increment version on regenerate. | P1 |
| LIB-3 | View, delete (confirm), regenerate. | P0 |
| LIB-4 | Export Markdown and Word with disclaimer. | P1 |
| LIB-5 | Actual reference count per paper, not a placeholder. | P2 |

#### NFR

| ID | Requirement | Priority |
|---|---|---|
| NFR-1 | RLS: a user only reads/writes their rows. | P0 |
| NFR-2 | Storage paths derived from `auth.uid()`, never trusted from the client. | P0 |
| NFR-3 | No PII fixtures (I-9, certificates, scans) in git. | P0 |
| NFR-4 | Indexing: first PDF produces visible chunks in under 2 minutes on a typical laptop/local stack. | P1 |
| NFR-5 | Generation: one section in under 2 minutes after retrieval. | P1 |
| NFR-6 | Keyboard-reachable primary flows (login, upload, generate). | P2 |
| NFR-7 | Tests: ingest of a fixture PDF; retrieval hit on a known query; generation refuses unknown citation ids. | P0 |

### 5. UX flow

1. Sign up, confirm email (or request a password reset), then sign in.
2. Dashboard: upload three sources — original research (`primary`), style examples, and reference literature. Mark each `"references"` file as literature or primary (this study).
3. Wait until files show as processed (not only “uploaded”).
4. Optional: Interrogate the corpus (defaults to supporting papers; can include original research and style examples); pin literature/primary passages into the draft.
5. Enter the research prompt, pick sections and paper type.
6. Optional: generate outline, edit, confirm.
7. Generate draft section by section; inspect retrieved passages.
8. Preview with flags; light edits.
9. Save to library; export.

Empty states: no files, no papers, failed parse, missing API key.

### 6. Success metrics (after generation ships)

Measure these; do not invent pass rates.

- Retrieval: recall@k on a 20-question holdout over a known corpus.
- Citation precision: share of emitted citations that exist in retrieved chunks.
- Unsupported-claim rate: share of sentences with no mapped span.
- Time: upload-to-indexed; prompt-to-first-section.

### 7. Risks

| Risk | Mitigation |
|---|---|
| Hallucinated citations | Hard allow-list of retrieved source ids; refuse the rest. |
| Mixing the user’s study with published papers | `source_role` on references; generate section retrieval prefers literature vs primary. Interrogate defaults to supporting papers and quotas 16/20 to literature when that source is on. |
| Naive whole-paper generation | Section-wise retrieval and generation; frozen type × section templates. |
| Academic misconduct if sold as “write my paper” | Product copy: drafting assistant; disclaimer on every export. |
| API keys in the browser | Server-only secret storage. |
| PII in the repo | `.docs/*.pdf` gitignored; never commit identity documents. |

### 8. MVP cut line

**Must ship for “MVP”:** AUTH-1–3, AUTH-5–8, DOCS-1, DOCS-4–6, DOCS-8, GEN-1–2, GEN-4–6, GEN-9–10, QUAL-1–2, QUAL-4, LIB-1, LIB-3, NFR-1–3, NFR-7.

Everything else can follow without pretending it is done.

## References

- `.docs/TECHNICAL_SPECIFICATION.md` — as-built and target architecture
- `.docs/GENERATION_SLICES.md` — generate build slices
- `.docs/GAP_ANALYSIS.md` — PRD vs code
- `supabase/migrations/20260906133100_init.sql` — current schema
- `.docs/legacy/AI_Research_Paper_Writer_User_Stories.markdown` — original stories (stale; superseded where they conflict)
