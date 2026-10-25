# BrandGuard AI — Intelligent Brand Governance Platform

Working full-stack prototype of the **Inkloom AI Brand Governance Platform Challenge**
submission described in [`Inkloom AI - Brand Governance Platform Solution Doc (PRD & TRD).md`](./Inkloom%20AI%20-%20Brand%20Governance%20Platform%20Solution%20Doc%20(PRD%20%26%20TRD).md).

BrandGuard AI inspects a draft **before publication** across four specialist agents —
tone & vocabulary, factual claims, visual compliance and accessibility — and returns
explainable findings with an exact guideline clause citation and a non-destructive fix.
Nothing is auto-published: a Manager/Admin/Legal role passes the approval gate.

**Round 2 pack:** [`docs/ROUND-2-SUBMISSION.md`](./docs/ROUND-2-SUBMISSION.md) (feature list,
technology, plan changes, three Round 3 improvements) · [`docs/DEPLOY.md`](./docs/DEPLOY.md)
(one-URL deployment and private-window checklist) · `docs/BrandGuard-AI-Round-2-Submission-DRAFT.pdf`
(regenerated with final links by `scripts/build_submission_pdf.py`).

---

## Stack

| Layer | Implementation |
| --- | --- |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, TanStack Query |
| Backend | Python 3.11+ / FastAPI, Pydantic v2 |
| Inspection engine | Deterministic multi-agent rules + TF-IDF retrieval (offline, no API keys) |
| Storage | SQLite (schema mirrors the TRD PostgreSQL design) |
| Postgres/pgvector | Documented upgrade path — single retrieval/persistence seam |

The demo can run entirely offline with no API keys, or as one public container where FastAPI
serves both the API and the exported Next.js UI from the same origin.

---

## Quickstart

Two terminals are required.

### 1. Backend (port 8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- On first boot the SQLite DB is created at `backend/data/brandguard.db` and seeded with
  **16 guideline clauses** and **5 historical scans** (so analytics is populated).

### 2. Frontend (port 3000)

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. If the API runs elsewhere, copy `frontend/.env.example` to
`frontend/.env.local` and set `NEXT_PUBLIC_API_URL`.

### One-command dev launcher (Windows)

```powershell
.\scripts\dev.ps1
```

### Single-URL deployment (judge-friendly)

The repo ships a multi-stage `Dockerfile` that builds the Next.js static export and serves it
from FastAPI, so the app and API share one origin and one public URL.

```powershell
docker build -t brandguard-ai .
docker run --rm -p 8000:8000 brandguard-ai
# open http://localhost:8000
```

Deploy the same container to Render with `render.yaml`, or use the split Vercel + API setup.
Step-by-step instructions, including the private-window check: [`docs/DEPLOY.md`](./docs/DEPLOY.md).

---

## Five-minute demo script

1. The workspace loads a deliberately non-compliant sample draft (“500% faster”, “guaranteed”,
   unsplash image, off-contrast colour, generic link text).
2. Click **Run inspection** → 16 findings across four agent tabs.
3. Open **Fact & Claims** → the critical claim cites *Approved Fact Sheet v2.1 §4.2* and
   points to the retired 500% figure in §4.5.
4. Click **Accept suggestion** → the draft is rewritten to “up to 150%”, the finding is marked
   *Accepted*, the score rises and the other findings are re-checked.
5. Use **Override / Comment** with a justification → the finding is suppressed on re-scan and
   logged in the **Activity** audit trail.
6. Switch the header role to **Manager**, then **Approve draft** → **Publish**.
7. Open **Insights** for KPIs, 30-day violation trend, inspector load, guideline clarity and
   the vector knowledge-base registry. Upload a Markdown/TXT policy to add new clauses.

A Creator is blocked from approving by the API (`403`); unresolved critical findings block
approval (`409`).

---

## Feature coverage

| PRD ID | Requirement | Where |
| --- | --- | --- |
| FR-INGEST | Guideline ingestion, chunking, retrieval | `backend/app/retrieval.py`, `/api/guidelines*` |
| FR-SCAN | Multi-modal inspection (tone, claims, visual, WCAG) | `backend/app/inspectors.py` |
| FR-EXPLAIN | Clause-level citations with exact quotes | findings → `citation` object |
| FR-SUGGEST | Context-preserving one-click fixes | `suggested_fix` + accept endpoint |
| FR-WORKFLOW | Role gates, overrides, comments, audit | `backend/app/pipeline.py` |
| FR-ANALYTICS | KPIs, trends, clarity index, KB registry | `/api/analytics`, `/analytics` |
| NFR performance | Single-pass deterministic inspection (ms, not seconds) | pipeline runs in-process |
| NFR accessibility | Skip links semantics, aria labels, contrast-safe UI | components |

Extras beyond the brief: search palette (`Ctrl/Cmd+K`), inline highlighted document canvas,
per-agent filters, score ring, activity/audit trail, upload-and-chunk policy docs, seeded demo
data, 11 API tests.

---

## Architecture

```
Next.js 14 (App Router, Tailwind, TanStack Query)
        │  fetch / REST
        ▼
FastAPI  ── routers ──► pipeline ──► inspectors (tone | claims | visual | a11y)
        │                   │
        │                   ├─► retrieval (TF-IDF; swap for pgvector + embeddings)
        │                   └─► SQLite (guidelines, scans, findings, comments, audit)
        ▼
OpenAPI docs / analytics aggregation
```

Key design decisions:

- **Offline determinism** — the hackathon demo must run from a clean clone with no keys.
  Every finding is reproducible, which makes the citation claims trustworthy.
- **Structured agent contract** — each inspector returns
  `{agent, code, severity, segment, offsets, explanation, suggested_fix}`. Swapping a rule
  agent for an LLM JSON-schema call does not change the pipeline, UI or API.
- **Character offsets** — findings carry `start_index` / `end_index`, enabling the
  split-pane inline highlights in the review canvas.
- **Stable finding IDs** — re-scans upsert by `(agent, issue_type, offending_segment)` so the UI
  keeps selection and overrides are not re-raised.
- **Human primacy** — overrides require a note; approvals are role-gated; every mutation writes
  `audit_events`.

### Production upgrade path

1. Replace SQLite with PostgreSQL 16 + `pgvector`; enable row-level security per tenant.
2. Swap TF-IDF in `retrieval.py` for `text-embedding-3-small` (1536-dim) + pgvector cosine.
3. Replace deterministic inspectors with LangChain/LlamaIndex structured-output chains, keeping
   the same draft schema; add a VLM for image/logo verification.
4. Move long scans to Celery + Redis; stream progress over WebSockets.
5. Add OIDC/JWT auth, per-tenant encryption, retention policies and webhook/CRM connectors.

---

## API surface

See [`backend/README.md`](./backend/README.md) for the full table. Highlights:

```text
POST /api/scans                              submit a draft → findings + citations
POST /api/scans/{id}/findings/{fid}/accept   apply one-click fix + re-check
POST /api/scans/{id}/findings/{fid}/override override with justification
POST /api/scans/{id}/approve                 manager gate (blocks critical findings)
GET  /api/analytics                          KPIs, 30-day trend, clarity, recent scans
GET  /api/knowledge-base/search?q=           retrieval over guideline clauses
POST /api/guidelines/upload                  chunk + index a policy document
```

---

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q      # 11 passed
cd ..\frontend
npm run build                                # type-check + production build
# static export used by the Docker image:
$env:NEXT_STATIC_EXPORT="1"; $env:NEXT_PUBLIC_API_URL="/"; npm run build
```

---

## Project layout

```
backend/
  app/
    main.py          FastAPI app + routes + analytics
    pipeline.py      scan lifecycle, resolution, approval gates, audit
    inspectors.py    four deterministic inspection agents + WCAG contrast utils
    retrieval.py     TF-IDF retrieval (pgvector seam)
    seed.py          guideline clauses + historical demo scans
    db.py            SQLite schema mirroring the TRD tables
    schemas.py       Pydantic request models
  tests/test_api.py  11 end-to-end API tests
frontend/
  app/               App Router pages: workspace + insights
  components/        header/search palette, split-pane workspace, findings, analytics
  lib/               typed API client, types, sample draft
docs/                Round 2 submission (Markdown + PDF) and deployment guide
Dockerfile           single image: Next static export served by FastAPI
render.yaml          free-tier Render blueprint
scripts/             dev launcher + submission PDF builder
```

---

## Demo data & privacy

The SQLite database lives in `backend/data/` (gitignored) and is safe to delete to reset the
demo. Seeded scans are synthetic and belong to the fictional “Acme Corp” tenant. Text is only
stored locally for review tracking; no external model calls are made.

## Known scope limits

- Policy uploads support **Markdown / TXT** in the demo; the TRD's DOCX/PDF parsing
  (Unstructured.io) is represented by `_chunk_markdown` in `backend/app/main.py` and is the
  intended integration point.
- Visual checks operate on Markdown image references, palette values and CSS-style colour
  codes. A production VLM pipeline would additionally inspect uploaded pixels for logo clear
  space and imagery provenance.
- Authentication, Celery/Redis workers and pgvector are documented upgrade paths, not part of
  the offline demo.

