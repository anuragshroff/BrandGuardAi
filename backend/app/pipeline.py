"""Scan pipeline: create -> inspect -> cite -> resolve -> approve -> publish."""

from __future__ import annotations

import uuid
from typing import Any

from . import db, inspectors
from .seed import ORG

STATUS_RANK = {"Pending": 0, "Flagged": 1, "Approved": 2, "Published": 3}


class PipelineError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _audit(conn, scan_id: str, actor: str, role: str, action: str, detail: str = "") -> None:
    conn.execute(
        """
        INSERT INTO audit_events (id, scan_id, actor, role, action, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), scan_id, actor, role, action, detail, db.now_iso()),
    )


def _compliance(findings: list[dict]) -> tuple[int, dict]:
    unresolved = [f for f in findings if f["status"] == "Unresolved"]
    penalty = sum(inspectors.SEVERITY_WEIGHT.get(f["severity"], 0) for f in unresolved)
    counts = {"critical": 0, "warning": 0, "info": 0}
    for finding in unresolved:
        counts[finding["severity"].lower()] += 1
    return max(0, 100 - penalty), counts


def create_scan(payload: dict, actor: str = "Dhanraj Sonar", role: str = "Creator") -> dict:
    content = payload.get("content", "").strip()
    if not content:
        raise PipelineError("Draft content is required.")
    if len(content) > 40_000:
        raise PipelineError("Draft is too large for a single scan (40,000 character limit).", 413)

    scan_id = str(uuid.uuid4())
    created = db.now_iso()
    with db.get_db() as conn:
        conn.execute(
            """
            INSERT INTO scans
                (id, organization_id, creator_id, document_title, raw_content, channel,
                 audience, region, campaign, status, compliance_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 100, ?, ?)
            """,
            (
                scan_id,
                ORG,
                actor,
                payload.get("title") or "Untitled draft",
                content,
                payload.get("channel", "Blog Post"),
                payload.get("audience", "Enterprise IT"),
                payload.get("region", "North America"),
                payload.get("campaign", "Q4 Global Launch"),
                created,
                created,
            ),
        )
        _audit(conn, scan_id, actor, role, "scan.created", f"{len(content)} characters submitted")

    run_inspection(scan_id)
    return serialize_scan(scan_id)


def run_inspection(scan_id: str, created_at: str | None = None) -> dict:
    """(Re)run all four agents and refresh open findings.

    Resolved findings are preserved for the audit trail.  Overridden findings
    act as suppressions so an approved exception is not re-raised on every re-scan.
    """
    with db.get_db() as conn:
        scan = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not scan:
            raise PipelineError("Scan not found.", 404)

        guidelines = {
            row["code"]: dict(row)
            for row in conn.execute("SELECT * FROM guidelines WHERE organization_id = ?", (ORG,))
        }

        preserved = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM findings WHERE scan_id = ? AND status != 'Unresolved'", (scan_id,)
            ).fetchall()
        ]
        suppressed = {
            (f["agent"], f["issue_type"], f["offending_segment"])
            for f in preserved
            if f["status"] == "Overridden"
        }

        existing_open = {
            (row["agent"], row["issue_type"], row["offending_segment"]): dict(row)
            for row in conn.execute(
                "SELECT * FROM findings WHERE scan_id = ? AND status = 'Unresolved'", (scan_id,)
            ).fetchall()
        }

        ctx = {
            "channel": scan["channel"],
            "audience": scan["audience"],
            "region": scan["region"],
            "campaign": scan["campaign"],
        }
        drafts = inspectors.run_agents(scan["raw_content"], ctx)
        stamp = created_at or db.now_iso()
        inserted = 0
        seen_keys: set[tuple[str, str, str]] = set()
        for draft in drafts:
            key = (draft["agent"], draft["issue_type"], draft["offending_segment"])
            if key in suppressed:
                continue
            seen_keys.add(key)
            guideline = guidelines.get(draft["code"])
            existing = existing_open.get(key)
            if existing:
                # Keep the finding id stable across re-scans so the UI can hold
                # selection and the API stays idempotent for clients.
                conn.execute(
                    """
                    UPDATE findings
                       SET guideline_id = ?, severity = ?, start_index = ?, end_index = ?,
                           explanation = ?, suggested_fix = ?
                     WHERE id = ?
                    """,
                    (
                        guideline["id"] if guideline else None,
                        draft["severity"],
                        draft["start_index"],
                        draft["end_index"],
                        draft["explanation"],
                        draft["suggested_fix"],
                        existing["id"],
                    ),
                )
                continue
            conn.execute(
                """
                INSERT INTO findings
                    (id, scan_id, guideline_id, agent, severity, issue_type, offending_segment,
                     start_index, end_index, explanation, suggested_fix, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Unresolved', ?)
                """,
                (
                    str(uuid.uuid4()),
                    scan_id,
                    guideline["id"] if guideline else None,
                    draft["agent"],
                    draft["severity"],
                    draft["issue_type"],
                    draft["offending_segment"],
                    draft["start_index"],
                    draft["end_index"],
                    draft["explanation"],
                    draft["suggested_fix"],
                    stamp,
                ),
            )
            inserted += 1

        stale = [row["id"] for key, row in existing_open.items() if key not in seen_keys]
        for finding_id in stale:
            conn.execute("DELETE FROM findings WHERE id = ?", (finding_id,))

    score, _counts = summarize(scan_id)
    findings = summarize_findings(scan_id)
    has_blocker = any(
        f["status"] == "Unresolved" and f["severity"] in ("Critical", "Warning")
        for f in findings
    )
    with db.get_db() as conn:
        current = conn.execute("SELECT status FROM scans WHERE id = ?", (scan_id,)).fetchone()["status"]
        if has_blocker:
            new_status = "Flagged"
        elif current in ("Approved", "Published"):
            new_status = current
        else:
            new_status = "Pending"
        conn.execute(
            "UPDATE scans SET status = ?, compliance_score = ?, updated_at = ? WHERE id = ?",
            (new_status, score, db.now_iso(), scan_id),
        )
    return {"inserted": inserted}


def summarize_findings(scan_id: str) -> list[dict]:
    with db.get_db() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM findings WHERE scan_id = ? ORDER BY created_at", (scan_id,)
            ).fetchall()
        ]


def summarize(scan_id: str) -> tuple[int, dict]:
    findings = summarize_findings(scan_id)
    return _compliance(findings)


def _finding(conn, scan_id: str, finding_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM findings WHERE id = ? AND scan_id = ?", (finding_id, scan_id)
    ).fetchone()
    if not row:
        raise PipelineError("Finding not found.", 404)
    return dict(row)


def accept_finding(
    scan_id: str,
    finding_id: str,
    *,
    actor: str = "Dhanraj Sonar",
    role: str = "Creator",
) -> dict:
    with db.get_db() as conn:
        finding = _finding(conn, scan_id, finding_id)
        if finding["status"] != "Unresolved":
            raise PipelineError("This finding has already been resolved.", 409)
        fix = finding["suggested_fix"]
        if not fix:
            raise PipelineError("This finding has no one-click fix. Add a comment or override.", 422)

        scan = conn.execute("SELECT raw_content FROM scans WHERE id = ?", (scan_id,)).fetchone()
        content = scan["raw_content"]
        start, end = finding["start_index"], finding["end_index"]
        segment = finding["offending_segment"]
        if content[start:end] == segment:
            updated = content[:start] + fix + content[end:]
        elif segment in content:
            updated = content.replace(segment, fix, 1)
        else:
            raise PipelineError("The draft changed since this finding was raised. Re-scan first.", 409)

        conn.execute(
            "UPDATE findings SET status='Accepted', resolution_note=?, resolved_by=?, "
            "resolved_at=? WHERE id=?",
            (f"Applied suggestion: {fix}", actor, db.now_iso(), finding_id),
        )
        conn.execute(
            "UPDATE scans SET raw_content = ?, updated_at = ? WHERE id = ?",
            (updated, db.now_iso(), scan_id),
        )
        _audit(conn, scan_id, actor, role, "finding.accepted", finding["issue_type"])

    run_inspection(scan_id)
    return serialize_scan(scan_id)


def override_finding(
    scan_id: str,
    finding_id: str,
    *,
    note: str,
    actor: str = "Dhanraj Sonar",
    role: str = "Manager",
) -> dict:
    if not note.strip():
        raise PipelineError("Overrides require a written justification.")
    with db.get_db() as conn:
        finding = _finding(conn, scan_id, finding_id)
        if finding["status"] != "Unresolved":
            raise PipelineError("This finding has already been resolved.", 409)
        conn.execute(
            "UPDATE findings SET status='Overridden', resolution_note=?, resolved_by=?, "
            "resolved_at=? WHERE id=?",
            (note.strip(), actor, db.now_iso(), finding_id),
        )
        _audit(conn, scan_id, actor, role, "finding.overridden", f"{finding['issue_type']}: {note.strip()}")

    run_inspection(scan_id)
    return serialize_scan(scan_id)


def add_comment(
    scan_id: str,
    *,
    body: str,
    author: str = "Dhanraj Sonar",
    role: str = "Creator",
    finding_id: str | None = None,
) -> dict:
    if not body.strip():
        raise PipelineError("Comment cannot be empty.")
    with db.get_db() as conn:
        conn.execute(
            """
            INSERT INTO comments (id, scan_id, finding_id, author, role, body, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), scan_id, finding_id, author, role, body.strip(), db.now_iso()),
        )
        _audit(conn, scan_id, author, role, "comment.created", body.strip()[:180])
    return serialize_scan(scan_id)


def approve_scan(
    scan_id: str, *, actor: str = "Brand Manager", role: str = "Manager"
) -> dict:
    if role not in ("Manager", "Admin", "Legal"):
        raise PipelineError("Only Manager, Admin or Legal roles can approve a scan.", 403)
    findings = summarize_findings(scan_id)
    blockers = [
        f for f in findings if f["status"] == "Unresolved" and f["severity"] == "Critical"
    ]
    if blockers:
        raise PipelineError(
            f"{len(blockers)} critical finding(s) must be resolved before approval.", 409
        )
    with db.get_db() as conn:
        conn.execute(
            "UPDATE scans SET status='Approved', updated_at=? WHERE id=?",
            (db.now_iso(), scan_id),
        )
        _audit(conn, scan_id, actor, role, "scan.approved")
    return serialize_scan(scan_id)


def publish_scan(scan_id: str, *, actor: str = "Brand Manager", role: str = "Manager") -> dict:
    if role not in ("Manager", "Admin", "Legal"):
        raise PipelineError("Only Manager, Admin or Legal roles can publish.", 403)
    with db.get_db() as conn:
        scan = conn.execute("SELECT status FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not scan:
            raise PipelineError("Scan not found.", 404)
        if scan["status"] != "Approved":
            raise PipelineError("Approve the scan before publishing.", 409)
        conn.execute(
            "UPDATE scans SET status='Published', updated_at=? WHERE id=?",
            (db.now_iso(), scan_id),
        )
        _audit(conn, scan_id, actor, role, "scan.published")
    return serialize_scan(scan_id)


def serialize_scan(scan_id: str) -> dict:
    with db.get_db() as conn:
        scan_row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not scan_row:
            raise PipelineError("Scan not found.", 404)
        scan = dict(scan_row)
        finding_rows = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM findings WHERE scan_id = ?", (scan_id,)
            ).fetchall()
        ]
        guideline_rows = {
            row["id"]: dict(row)
            for row in conn.execute("SELECT * FROM guidelines").fetchall()
        }
        comments = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM comments WHERE scan_id = ? ORDER BY created_at", (scan_id,)
            ).fetchall()
        ]
        audit = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM audit_events WHERE scan_id = ? ORDER BY created_at", (scan_id,)
            ).fetchall()
        ]

    findings = []
    for row in finding_rows:
        guideline = guideline_rows.get(row["guideline_id"]) if row["guideline_id"] else None
        row["citation"] = (
            {
                "guideline_id": guideline["id"],
                "code": guideline["code"],
                "title": guideline["title"],
                "section": guideline["section"],
                "category": guideline["category"],
                "quote": guideline["content"],
            }
            if guideline
            else None
        )
        row["ai_generated"] = True
        findings.append(row)

    findings.sort(
        key=lambda f: (
            inspectors.SEVERITY_ORDER[f["severity"]],
            f["start_index"],
            f["created_at"],
        )
    )

    score, counts = _compliance(findings)
    counts["unresolved"] = sum(1 for f in findings if f["status"] == "Unresolved")
    scan["findings"] = findings
    scan["comments"] = comments
    scan["audit"] = audit
    scan["compliance_score"] = score
    scan["summary"] = counts
    return scan
