"""Inspection engine + API contract tests.

Run with:  pytest -q  (inside backend/)
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BRANDGUARD_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRANDGUARD_SEED_DEMO", "0")

    from app import db, main

    importlib.reload(db)
    importlib.reload(main)
    with TestClient(main.app) as test_client:
        yield test_client


SAMPLE = (
    "Our revolutionary platform speeds up workflows by 500% and is the industry leader. "
    "We guarantee results for 42,000 customers. Use the tool today. "
    "![logo](https://cdn.acme.com/brand/acme-logo.png)"
)


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_seeded_knowledge_base(client):
    payload = client.get("/api/guidelines").json()
    assert payload["total_chunks"] >= 15
    codes = {item["code"] for item in payload["items"]}
    assert {"FACT-4.2", "A11Y-5.2", "TONE-2.1"} <= codes


def test_scan_flags_critical_claim_with_citation(client):
    scan = client.post(
        "/api/scans",
        json={"title": "Launch post", "content": SAMPLE, "channel": "Blog Post"},
    ).json()

    assert scan["status"] == "Flagged"
    assert scan["summary"]["critical"] >= 1
    assert scan["compliance_score"] < 100

    claim = next(f for f in scan["findings"] if f["issue_type"] == "Unverified performance claim")
    assert claim["severity"] == "Critical"
    assert claim["citation"]["code"] == "FACT-4.2"
    assert "150%" in claim["citation"]["quote"]
    assert claim["suggested_fix"] == "up to 150%"
    assert claim["ai_generated"] is True


def test_every_finding_is_cited(client):
    scan = client.post("/api/scans", json={"title": "Cited", "content": SAMPLE}).json()
    assert scan["findings"]
    for finding in scan["findings"]:
        assert finding["citation"] is not None
        assert finding["citation"]["quote"]
        assert finding["citation"]["section"]


def test_accept_suggestion_rewrites_content(client):
    scan = client.post("/api/scans", json={"title": "Fix me", "content": SAMPLE}).json()
    claim = next(f for f in scan["findings"] if f["issue_type"] == "Unverified performance claim")

    updated = client.post(
        f"/api/scans/{scan['id']}/findings/{claim['id']}/accept",
        json={"actor": "Dhanraj Sonar", "role": "Creator"},
    ).json()

    assert "500%" not in updated["raw_content"]
    assert "up to 150%" in updated["raw_content"]
    accepted = next(f for f in updated["findings"] if f["id"] == claim["id"])
    assert accepted["status"] == "Accepted"


def test_override_requires_note_and_is_not_retriggered(client):
    scan = client.post("/api/scans", json={"title": "Override", "content": SAMPLE}).json()
    finding = next(f for f in scan["findings"] if f["issue_type"] == "Hype vocabulary")

    rejected = client.post(
        f"/api/scans/{scan['id']}/findings/{finding['id']}/override",
        json={"note": "  "},
    )
    assert rejected.status_code == 400

    updated = client.post(
        f"/api/scans/{scan['id']}/findings/{finding['id']}/override",
        json={"note": "Legal approved this phrasing.", "role": "Manager"},
    ).json()

    overridden = next(f for f in updated["findings"] if f["id"] == finding["id"])
    assert overridden["status"] == "Overridden"
    duplicates = [
        f for f in updated["findings"]
        if f["issue_type"] == finding["issue_type"]
        and f["offending_segment"] == finding["offending_segment"]
        and f["status"] == "Unresolved"
    ]
    assert duplicates == []


def test_approval_gate_blocks_critical_and_allows_manager(client):
    scan = client.post("/api/scans", json={"title": "Approve me", "content": SAMPLE}).json()

    blocked = client.post(
        f"/api/scans/{scan['id']}/approve",
        json={"actor": "Creator", "role": "Creator"},
    )
    assert blocked.status_code == 403

    blocked = client.post(
        f"/api/scans/{scan['id']}/approve",
        json={"actor": "Manager", "role": "Manager"},
    )
    assert blocked.status_code == 409

    for finding in scan["findings"]:
        if finding["severity"] == "Critical" and finding["status"] == "Unresolved":
            client.post(
                f"/api/scans/{scan['id']}/findings/{finding['id']}/override",
                json={"note": "Risk accepted for internal draft.", "role": "Manager"},
            )

    approved = client.post(
        f"/api/scans/{scan['id']}/approve",
        json={"actor": "Brand Manager", "role": "Manager"},
    ).json()
    assert approved["status"] == "Approved"

    published = client.post(
        f"/api/scans/{scan['id']}/publish",
        json={"actor": "Brand Manager", "role": "Manager"},
    ).json()
    assert published["status"] == "Published"


def test_accessibility_and_visual_agents(client):
    content = (
        "The dashboard text color #F5B700 looks great on a white background. "
        "![dashboard](https://images.unsplash.com/photo-1) Click here for details."
    )
    scan = client.post("/api/scans", json={"title": "A11y", "content": content}).json()
    issue_types = {f["issue_type"] for f in scan["findings"]}
    assert "Insufficient alternative text" in issue_types
    assert "Insufficient colour contrast" in issue_types
    assert "Unauthorised imagery" in issue_types
    assert "Ambiguous link text" in issue_types


def test_knowledge_base_search_ranks_claims(client):
    results = client.get(
        "/api/knowledge-base/search", params={"q": "performance benchmark percentage"}
    ).json()["items"]
    assert results
    assert results[0]["code"] in {"FACT-4.2", "FACT-4.5"}


def test_policy_upload_is_chunked_and_indexed(client):
    document = (
        "# Partner logo lockup\n\n"
        "Partner logos sit in the secondary lockup with a 24px gutter on all sides.\n\n"
        "# Joint claim approvals\n\n"
        "Any joint claim with a partner must be re-approved by Legal every 12 months.\n"
    )
    response = client.post(
        "/api/guidelines/upload",
        files={"file": ("partner-rules.md", document.encode("utf-8"), "text/markdown")},
        data={"category": "Visual", "title": "Partner Co-branding Rules 2027"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["chunks"] == 2
    assert all(item["category"] == "Visual" for item in payload["items"])
    assert any("24px" in item["content"] for item in payload["items"])

    listing = client.get("/api/guidelines").json()
    assert listing["total_chunks"] >= 18


def test_analytics_shape(client):
    client.post("/api/scans", json={"title": "Metrics", "content": SAMPLE})
    data = client.get("/api/analytics").json()
    assert data["totals"]["scans"] == 1
    assert len(data["trend"]) == 30
    assert data["severity"]["Critical"] >= 1
    assert data["clarity"]
    assert data["recent_scans"]
