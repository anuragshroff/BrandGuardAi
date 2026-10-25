"""FastAPI application: REST API for BrandGuard AI."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, pipeline, retrieval, schemas, seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    seed.seed_all()
    yield


app = FastAPI(
    title="BrandGuard AI",
    description=(
        "Intelligent brand governance platform. Pre-publication inspection across tone, "
        "claims, visual and accessibility with clause-level citations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "BRANDGUARD_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(pipeline.PipelineError)
async def pipeline_error_handler(_request, exc: pipeline.PipelineError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "brandguard-api", "version": app.version}


# ---------------------------------------------------------------------------
# Guidelines / knowledge base
# ---------------------------------------------------------------------------

@app.get("/api/guidelines")
def list_guidelines(category: str | None = None) -> dict:
    with db.get_db() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM guidelines WHERE category = ? ORDER BY code", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM guidelines ORDER BY code").fetchall()
    return {"items": [dict(row) for row in rows], **retrieval.stats()}


@app.post("/api/guidelines", status_code=201)
def create_guideline(payload: schemas.GuidelineCreate) -> dict:
    guideline_id = str(uuid.uuid4())
    code = payload.code or f"UPLOAD-{guideline_id[:6].upper()}"
    with db.get_db() as conn:
        conn.execute(
            """
            INSERT INTO guidelines
                (id, organization_id, code, title, category, section, content, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guideline_id,
                seed.ORG,
                code,
                payload.title,
                payload.category,
                payload.section,
                payload.content,
                payload.tags,
                db.now_iso(),
            ),
        )
        row = conn.execute("SELECT * FROM guidelines WHERE id = ?", (guideline_id,)).fetchone()
    return dict(row)


def _chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Split an uploaded policy doc into (heading, body) chunks."""
    chunks: list[tuple[str, str]] = []
    heading = "Uploaded policy"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if len(body) >= 40:
            chunks.append((heading, body))

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip() or heading
            buffer = []
        elif not stripped:
            if sum(len(part) for part in buffer) > 320:
                flush()
                buffer = []
        else:
            buffer.append(stripped)
    flush()
    return chunks or [(heading, text.strip()[:4000])]


@app.post("/api/guidelines/upload", status_code=201)
async def upload_guideline(
    file: UploadFile = File(...),
    category: str = Form("Tone"),
    title: str = Form(""),
) -> dict:
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="File is larger than 5 MB.")
    text = raw.decode("utf-8", errors="ignore")
    doc_title = title.strip() or (file.filename or "Uploaded policy").rsplit(".", 1)[0]
    chunks = _chunk_markdown(text)
    created = db.now_iso()
    items = []
    with db.get_db() as conn:
        for index, (heading, body) in enumerate(chunks, start=1):
            guideline_id = str(uuid.uuid4())
            code = f"UPLOAD-{guideline_id[:6].upper()}-{index}"
            conn.execute(
                """
                INSERT INTO guidelines
                    (id, organization_id, code, title, category, section, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guideline_id,
                    seed.ORG,
                    code,
                    doc_title,
                    category,
                    heading,
                    body,
                    f"upload,{category.lower()}",
                    created,
                ),
            )
            items.append(
                {
                    "id": guideline_id,
                    "code": code,
                    "title": doc_title,
                    "category": category,
                    "section": heading,
                    "content": body,
                    "tags": f"upload,{category.lower()}",
                    "created_at": created,
                }
            )
    return {"filename": file.filename, "chunks": len(items), "items": items}


@app.delete("/api/guidelines/{guideline_id}", status_code=204)
def delete_guideline(guideline_id: str):
    with db.get_db() as conn:
        conn.execute(
            "UPDATE findings SET guideline_id = NULL WHERE guideline_id = ?", (guideline_id,)
        )
        cursor = conn.execute("DELETE FROM guidelines WHERE id = ?", (guideline_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Guideline not found.")
    return None


@app.get("/api/knowledge-base/search")
def search_knowledge_base(q: str = Query(default=""), limit: int = Query(default=5, ge=1, le=20)) -> dict:
    results = retrieval.search(q, limit=limit)
    return {"query": q, "items": results}


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

@app.post("/api/scans", status_code=201)
def create_scan(payload: schemas.ScanCreate) -> dict:
    return pipeline.create_scan(payload.model_dump(), actor=payload.actor, role=payload.role)


@app.get("/api/scans")
def list_scans(limit: int = Query(default=25, ge=1, le=100)) -> dict:
    with db.get_db() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        ]
        items = []
        for row in rows:
            counts = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN severity='Critical' AND status='Unresolved' THEN 1 ELSE 0 END) AS critical,
                    SUM(CASE WHEN severity='Warning'  AND status='Unresolved' THEN 1 ELSE 0 END) AS warning,
                    SUM(CASE WHEN severity='Info'     AND status='Unresolved' THEN 1 ELSE 0 END) AS info,
                    SUM(CASE WHEN status='Unresolved' THEN 1 ELSE 0 END) AS unresolved
                FROM findings WHERE scan_id = ?
                """,
                (row["id"],),
            ).fetchone()
            row["summary"] = {
                "critical": counts["critical"] or 0,
                "warning": counts["warning"] or 0,
                "info": counts["info"] or 0,
                "unresolved": counts["unresolved"] or 0,
            }
            items.append(row)
    return {"items": items}


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
    return pipeline.serialize_scan(scan_id)


@app.post("/api/scans/{scan_id}/findings/{finding_id}/accept")
def accept_finding(scan_id: str, finding_id: str, payload: schemas.FindingAction) -> dict:
    return pipeline.accept_finding(
        scan_id, finding_id, actor=payload.actor, role=payload.role
    )


@app.post("/api/scans/{scan_id}/findings/{finding_id}/override")
def override_finding(scan_id: str, finding_id: str, payload: schemas.FindingAction) -> dict:
    return pipeline.override_finding(
        scan_id, finding_id, note=payload.note, actor=payload.actor, role=payload.role
    )


@app.post("/api/scans/{scan_id}/comments")
def add_comment(scan_id: str, payload: schemas.CommentCreate) -> dict:
    return pipeline.add_comment(
        scan_id,
        body=payload.body,
        author=payload.author,
        role=payload.role,
        finding_id=payload.finding_id,
    )


@app.post("/api/scans/{scan_id}/approve")
def approve_scan(scan_id: str, payload: schemas.ApprovalAction) -> dict:
    return pipeline.approve_scan(scan_id, actor=payload.actor, role=payload.role)


@app.post("/api/scans/{scan_id}/publish")
def publish_scan(scan_id: str, payload: schemas.ApprovalAction) -> dict:
    return pipeline.publish_scan(scan_id, actor=payload.actor, role=payload.role)


# ---------------------------------------------------------------------------
# Governance analytics
# ---------------------------------------------------------------------------

def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@app.get("/api/analytics")
def analytics() -> dict:
    now = datetime.now(timezone.utc)
    with db.get_db() as conn:
        scans = [dict(row) for row in conn.execute("SELECT * FROM scans").fetchall()]
        findings = [dict(row) for row in conn.execute("SELECT * FROM findings").fetchall()]
        guidelines = [dict(row) for row in conn.execute("SELECT * FROM guidelines").fetchall()]

    total_scans = len(scans)
    compliance_rate = (
        round(sum(scan["compliance_score"] for scan in scans) / total_scans, 1)
        if total_scans
        else 0.0
    )

    issue_types: dict[str, int] = {}
    for finding in findings:
        issue_types[finding["issue_type"]] = issue_types.get(finding["issue_type"], 0) + 1
    top_violation = max(issue_types.items(), key=lambda item: item[1])[0] if issue_types else "—"
    top_violation_share = (
        round(100 * issue_types.get(top_violation, 0) / len(findings), 1) if findings else 0.0
    )

    resolved = [f for f in findings if f["resolved_at"]]
    durations = []
    for finding in resolved:
        start, end = _parse(finding["created_at"]), _parse(finding["resolved_at"])
        if start and end:
            durations.append(max(0.0, (end - start).total_seconds() / 60))
    avg_resolution = round(sum(durations) / len(durations), 1) if durations else 0.0

    severity = {"Critical": 0, "Warning": 0, "Info": 0}
    for finding in findings:
        severity[finding["severity"]] = severity.get(finding["severity"], 0) + 1

    agent_labels = {
        "tone": "Tone & Vocabulary",
        "claim": "Fact & Claims",
        "visual": "Visual Compliance",
        "accessibility": "Accessibility",
    }
    agents = {label: 0 for label in agent_labels.values()}
    for finding in findings:
        label = agent_labels.get(finding["agent"])
        if label:
            agents[label] += 1

    start_day = (now - timedelta(days=29)).date()
    trend = []
    for offset in range(30):
        day = start_day + timedelta(days=offset)
        trend.append(
            {
                "date": day.isoformat(),
                "Critical": 0,
                "Warning": 0,
                "Info": 0,
            }
        )
    by_day = {item["date"]: item for item in trend}
    for finding in findings:
        stamp = _parse(finding["created_at"])
        if stamp and stamp.date().isoformat() in by_day:
            by_day[stamp.date().isoformat()][finding["severity"]] += 1

    clarity = []
    for guideline in guidelines:
        related = [f for f in findings if f["guideline_id"] == guideline["id"]]
        overrides = [f for f in related if f["status"] == "Overridden"]
        override_rate = round(100 * len(overrides) / len(related), 1) if related else 0.0
        clarity.append(
            {
                "code": guideline["code"],
                "title": guideline["title"],
                "section": guideline["section"],
                "category": guideline["category"],
                "findings": len(related),
                "overrides": len(overrides),
                "clarity": round(100 - override_rate, 1),
            }
        )
    clarity.sort(key=lambda item: (item["clarity"], -item["findings"]))

    recent = sorted(scans, key=lambda scan: scan["created_at"], reverse=True)[:6]
    recent_items = [
        {
            "id": scan["id"],
            "title": scan["document_title"],
            "channel": scan["channel"],
            "status": scan["status"],
            "compliance_score": scan["compliance_score"],
            "created_at": scan["created_at"],
            "unresolved": sum(
                1
                for finding in findings
                if finding["scan_id"] == scan["id"] and finding["status"] == "Unresolved"
            ),
        }
        for scan in recent
    ]

    return {
        "totals": {
            "scans": total_scans,
            "compliance_rate": compliance_rate,
            "top_violation": top_violation,
            "top_violation_share": top_violation_share,
            "avg_resolution_minutes": avg_resolution,
            "open_findings": sum(1 for f in findings if f["status"] == "Unresolved"),
            "guideline_chunks": len(guidelines),
        },
        "severity": severity,
        "agents": agents,
        "trend": trend,
        "clarity": clarity,
        "recent_scans": recent_items,
        "knowledge_base": retrieval.stats(),
    }


# ---------------------------------------------------------------------------
# Single-container deployment: serve the exported Next.js app when present.
# In local development run Next on :3000 and this block is inert (no `out/`).
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(
    os.getenv("FRONTEND_DIST", str(Path(__file__).resolve().parents[2] / "frontend" / "out"))
).resolve()

if (FRONTEND_DIST / "_next").is_dir():
    app.mount(
        "/_next",
        StaticFiles(directory=str(FRONTEND_DIST / "_next")),
        name="next-assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    if not FRONTEND_DIST.is_dir():
        if not full_path:
            return {
                "service": "brandguard-api",
                "status": "ok",
                "docs": "/docs",
                "hint": "Build the frontend with NEXT_STATIC_EXPORT=1 to serve it from this origin.",
            }
        raise HTTPException(status_code=404, detail="Not found")

    target = (FRONTEND_DIST / full_path).resolve()
    if target != FRONTEND_DIST and FRONTEND_DIST not in target.parents:
        raise HTTPException(status_code=404, detail="Not found")
    if target.is_file():
        return FileResponse(target)

    for candidate in (
        FRONTEND_DIST / full_path / "index.html",
        FRONTEND_DIST / f"{full_path}.html",
    ):
        if candidate.is_file():
            return FileResponse(candidate)

    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")
