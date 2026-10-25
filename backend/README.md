# Backend

FastAPI service for BrandGuard AI: guideline ingestion, multi-agent inspection,
citation engine, review workflow and governance analytics. Runs fully offline
with SQLite and deterministic rules; no API keys required.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

The SQLite database is created at `backend/data/brandguard.db` on first boot and
seeded with 16 guideline clauses plus five historical scans (set
`BRANDGUARD_SEED_DEMO=0` to skip the demo scans).

## Test

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness probe |
| GET/POST | `/api/guidelines` | List / add guideline clauses |
| POST | `/api/guidelines/upload` | Chunked upload of a policy document |
| DELETE | `/api/guidelines/{id}` | Remove a clause |
| GET | `/api/knowledge-base/search?q=` | Retrieval over the KB |
| POST/GET | `/api/scans` | Submit a draft / list scans |
| GET | `/api/scans/{id}` | Full scan, findings, citations, audit |
| POST | `/api/scans/{id}/findings/{fid}/accept` | Apply suggested fix |
| POST | `/api/scans/{id}/findings/{fid}/override` | Override with justification |
| POST | `/api/scans/{id}/comments` | Inline comment |
| POST | `/api/scans/{id}/approve` | Role-gated approval |
| POST | `/api/scans/{id}/publish` | Role-gated publish |
| GET | `/api/analytics` | KPIs, trend, clarity, recent scans |

## Design notes

- `inspectors.py` contains four pure agents (tone/vocabulary, claims, visual,
  accessibility). Each returns structured drafts with character offsets so the
  UI can render inline highlights.
- `pipeline.py` joins drafts to `guidelines` by `code`, persists findings and
  recomputes compliance. Overridden findings are treated as suppressions and are
  not re-raised on re-scan; accepted fixes mutate the draft and trigger a recheck.
- `retrieval.py` is TF-IDF cosine for the demo. It is the only retrieval entry
  point: replace it with pgvector + `text-embedding-3-small` for production.
- Every mutating action writes an `audit_events` row (human-in-the-loop trail).
- When `FRONTEND_DIST` points at an exported Next.js `out/` directory (the Docker
  image sets it to `/app/static`), this service also serves the UI and falls back
  to `index.html` for client-side routes. API routes take precedence.
