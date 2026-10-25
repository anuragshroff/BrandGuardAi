"""SQLite persistence layer.

The local demo intentionally uses SQLite (stdlib `sqlite3`) so the project runs
with zero infrastructure.  The schema mirrors the TRD PostgreSQL design
(brand_guidelines / content_scans / flagged_issues) and can be ported to
Postgres + pgvector by swapping this module - every query is plain SQL.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "brandguard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS guidelines (
    id              TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    code            TEXT NOT NULL,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    section         TEXT NOT NULL,
    content         TEXT NOT NULL,
    tags            TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id               TEXT PRIMARY KEY,
    organization_id  TEXT NOT NULL,
    creator_id       TEXT NOT NULL,
    document_title   TEXT NOT NULL,
    raw_content      TEXT NOT NULL,
    channel          TEXT NOT NULL DEFAULT '',
    audience         TEXT NOT NULL DEFAULT '',
    region           TEXT NOT NULL DEFAULT '',
    campaign         TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL,
    compliance_score INTEGER NOT NULL DEFAULT 100,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id                TEXT PRIMARY KEY,
    scan_id           TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    guideline_id      TEXT REFERENCES guidelines(id),
    agent             TEXT NOT NULL,
    severity          TEXT NOT NULL,
    issue_type        TEXT NOT NULL,
    offending_segment TEXT NOT NULL,
    start_index       INTEGER NOT NULL DEFAULT 0,
    end_index         INTEGER NOT NULL DEFAULT 0,
    explanation       TEXT NOT NULL,
    suggested_fix     TEXT,
    status            TEXT NOT NULL DEFAULT 'Unresolved',
    resolution_note   TEXT,
    resolved_by       TEXT,
    resolved_at       TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id         TEXT PRIMARY KEY,
    scan_id    TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    finding_id TEXT REFERENCES findings(id) ON DELETE CASCADE,
    author     TEXT NOT NULL,
    role       TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id         TEXT PRIMARY KEY,
    scan_id    TEXT REFERENCES scans(id) ON DELETE CASCADE,
    actor      TEXT NOT NULL,
    role       TEXT NOT NULL,
    action     TEXT NOT NULL,
    detail     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_scan ON audit_events(scan_id);
"""


def db_path() -> Path:
    """Resolved at call time so tests can point BRANDGUARD_DB at a tmp dir."""
    return Path(os.getenv("BRANDGUARD_DB", str(DEFAULT_DB))).expanduser().resolve()


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def org_id() -> str:
    return os.getenv("BRANDGUARD_ORG", "acme")


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
