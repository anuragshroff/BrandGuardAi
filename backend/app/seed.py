"""Seed data: the demo brand knowledge base and historical scans.

Every guideline chunk below is a citation target.  The inspection engine links
findings to these rows by `code`, which is what powers the "explainable
governance" requirement (every flag cites an exact guideline clause).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from . import db

ORG = "acme"

GUIDELINES: list[dict] = [
    {
        "code": "TONE-2.1",
        "title": "Global Brand Voice & Tone Guidelines 2026",
        "category": "Tone",
        "section": "§2.1 Voice principles",
        "content": (
            "Write in a confident, helpful, plain-spoken voice. Avoid hype words and "
            "unverifiable adjectives such as revolutionary, game-changing, cheap, fast or "
            "world-class. Prefer concrete, measurable language."
        ),
        "tags": "tone,voice,hype,plain-language",
    },
    {
        "code": "TONE-2.2",
        "title": "Global Brand Voice & Tone Guidelines 2026",
        "category": "Tone",
        "section": "§2.2 Superlatives & leadership claims",
        "content": (
            "Superlatives and leadership claims (industry leader, #1, world's best) may only "
            "be used when a current third-party ranking is cited in the same paragraph."
        ),
        "tags": "tone,superlatives,leadership",
    },
    {
        "code": "EDIT-4.1",
        "title": "Editorial Style Guide 2026",
        "category": "Tone",
        "section": "§4.1 Readability target",
        "content": (
            "Body copy should target a Flesch-Kincaid grade level of 9 or lower. Split "
            "sentences longer than 25 words and prefer short paragraphs of 3-4 sentences."
        ),
        "tags": "readability,grade-level,editorial",
    },
    {
        "code": "LEX-3.2",
        "title": "Brand Lexicon 2026",
        "category": "Vocabulary",
        "section": "§3.2 Approved product vocabulary",
        "content": (
            "Use 'customers' rather than 'users', and 'workspace' rather than 'tool'. "
            "Product names are always written as 'Acme Flow' and are never abbreviated."
        ),
        "tags": "vocabulary,lexicon,product-names",
    },
    {
        "code": "FACT-4.2",
        "title": "Approved Fact Sheet v2.1",
        "category": "Claim",
        "section": "§4.2 Verified performance benchmark",
        "content": (
            "Verified performance benchmark is up to 150% average speedup in production "
            "deployments. Any performance percentage above 150% is unsupported."
        ),
        "tags": "claims,performance,benchmark",
    },
    {
        "code": "FACT-4.5",
        "title": "Approved Fact Sheet v2.1",
        "category": "Claim",
        "section": "§4.5 Retired metrics",
        "content": (
            "The '500% faster' figure was retired in 2024 and must not be used in any "
            "collateral. Superseded metrics include 500%, 10x output and '2x revenue overnight'."
        ),
        "tags": "claims,retired,metrics",
    },
    {
        "code": "FACT-4.6",
        "title": "Approved Fact Sheet v2.1",
        "category": "Claim",
        "section": "§4.6 Customer & scale metrics",
        "content": (
            "Customer count claims must cite the current audited metric: 18,400 customers "
            "as of Q2 2026. Do not round customer counts up or down."
        ),
        "tags": "claims,customers,scale",
    },
    {
        "code": "LEGAL-3.1",
        "title": "Legal Disclaimer Policy",
        "category": "Claim",
        "section": "§3.1 Pricing & promotional claims",
        "content": (
            "Promotional pricing, discount codes and availability claims must state an "
            "expiry date and include 'terms apply'. Example: '30% off (terms apply; offer "
            "ends 31 Dec 2026)'."
        ),
        "tags": "legal,pricing,promotions,disclaimer",
    },
    {
        "code": "LEGAL-3.2",
        "title": "Legal Disclaimer Policy",
        "category": "Claim",
        "section": "§3.2 Prohibited guarantees",
        "content": (
            "Never guarantee outcomes. Terms such as guaranteed, risk-free, no-risk and 100% "
            "are prohibited in marketing copy. Describe documented results and add 'results "
            "may vary' where relevant."
        ),
        "tags": "legal,guarantees,risk",
    },
    {
        "code": "EDIT-2.4",
        "title": "Content Freshness Standard 2026",
        "category": "Claim",
        "section": "§2.4 Claim recency",
        "content": (
            "Statistics and dated claims must be no older than 18 months. Remove or refresh "
            "any year reference older than the current fiscal year."
        ),
        "tags": "claims,recency,freshness",
    },
    {
        "code": "VIS-1.3",
        "title": "Visual Identity Manual 2026",
        "category": "Visual",
        "section": "§1.3 Logo clear space",
        "content": (
            "The Acme logo requires clear space equal to 1x the logo height on all sides and "
            "must use the approved master asset (acme-logo-approved.svg). Never recolour, "
            "stretch or place the logo on a busy photo."
        ),
        "tags": "visual,logo,clear-space",
    },
    {
        "code": "VIS-1.6",
        "title": "Visual Identity Manual 2026",
        "category": "Visual",
        "section": "§1.6 Approved palette",
        "content": (
            "Only the approved brand palette may be used in marketing layouts: "
            "#0B1F3A (Ink Navy), #2F6BFF (Signal Blue), #F5B700 (Spark Amber) and #FFFFFF. "
            "Spark Amber is an accent only and is not accessible as body text on white."
        ),
        "tags": "visual,palette,colour",
    },
    {
        "code": "VIS-2.2",
        "title": "Visual Identity Manual 2026",
        "category": "Visual",
        "section": "§2.2 Approved imagery",
        "content": (
            "Only imagery from the approved asset library (cdn.acme.com/brand) may be used "
            "in external collateral. Third-party stock photography and placeholder images "
            "are prohibited without written approval."
        ),
        "tags": "visual,imagery,stock-photos",
    },
    {
        "code": "A11Y-5.2",
        "title": "Accessibility Standard (WCAG 2.1 AA)",
        "category": "Accessibility",
        "section": "§5.2 Alternative text",
        "content": (
            "Every non-decorative image must include descriptive alternative text of at "
            "least 5 words that conveys the purpose of the image. Decorative images use an "
            "empty alt attribute."
        ),
        "tags": "accessibility,alt-text,wcag",
    },
    {
        "code": "A11Y-5.4",
        "title": "Accessibility Standard (WCAG 2.1 AA)",
        "category": "Accessibility",
        "section": "§5.4 Colour contrast",
        "content": (
            "Text must maintain a contrast ratio of at least 4.5:1 against its background. "
            "Do not rely on colour alone to convey meaning. Spark Amber (#F5B700) on white "
            "fails at 1.9:1 and must not be used for text."
        ),
        "tags": "accessibility,contrast,wcag",
    },
    {
        "code": "A11Y-5.6",
        "title": "Accessibility Standard (WCAG 2.1 AA)",
        "category": "Accessibility",
        "section": "§5.6 Link purpose",
        "content": (
            "Link text must describe the destination. Avoid generic labels such as "
            "'click here', 'read more' or 'learn more' without an accessible name."
        ),
        "tags": "accessibility,links,wcag",
    },
]


DEMO_SCANS: list[dict] = [
    {
        "title": "Q4 Launch - Enterprise announcement",
        "channel": "Blog Post",
        "audience": "Enterprise IT",
        "region": "North America",
        "days_ago": 2,
        "content": (
            "# Acme Flow is here\n\n"
            "Our revolutionary platform speeds up campaign workflows by 500% and is already "
            "the industry leader. Get 25% off your first year with code LAUNCH25.\n\n"
            "![logo](https://cdn.acme.com/brand/acme-logo.png)\n"
        ),
    },
    {
        "title": "Agency brief - Performance landing page",
        "channel": "Landing Page",
        "audience": "Marketing Ops",
        "region": "EMEA",
        "days_ago": 5,
        "content": (
            "Teams using Acme Flow see a 10x lift in output. Our customers are guaranteed "
            "results and 42,000 customers already trust the tool.\n\n"
            "![dashboard](https://images.unsplash.com/photo-1522202176988-66273c2fd55f)\n"
        ),
    },
    {
        "title": "Lifecycle email - Win-back",
        "channel": "Email",
        "audience": "SMB",
        "region": "North America",
        "days_ago": 9,
        "content": (
            "Acme Flow is a cheap and fast solution for every team. Click here to claim "
            "your 30% discount before it is gone.\n"
        ),
    },
    {
        "title": "Product page - Governance module",
        "channel": "Website",
        "audience": "Brand Managers",
        "region": "Global",
        "days_ago": 14,
        "content": (
            "Acme Flow gives brand teams a single workspace for approvals. Our platform "
            "delivers up to 150% average speedup in production deployments, measured across "
            "18,400 customers in Q2 2026.\n\n"
            "![Acme Flow approval dashboard showing three pending reviews]"
            "(https://cdn.acme.com/brand/dashboard-approvals.png)\n"
        ),
    },
    {
        "title": "Paid social - Regional promo",
        "channel": "Social",
        "audience": "SMB",
        "region": "APAC",
        "days_ago": 21,
        "content": (
            "Save 40% on Acme Flow this quarter. The dashboard text color #F5B700 looks "
            "great on white backgrounds, and setup takes minutes.\n"
        ),
    },
]


def _guideline_id(code: str) -> str:
    return f"gl-{code.lower().replace('.', '-')}"


def seed_guidelines() -> int:
    with db.get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM guidelines").fetchone()["n"]
        if existing:
            return 0
        created = db.now_iso()
        for item in GUIDELINES:
            conn.execute(
                """
                INSERT INTO guidelines
                    (id, organization_id, code, title, category, section, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _guideline_id(item["code"]),
                    ORG,
                    item["code"],
                    item["title"],
                    item["category"],
                    item["section"],
                    item["content"],
                    item["tags"],
                    created,
                ),
            )
    return len(GUIDELINES)


def seed_demo_scans() -> int:
    """Create a handful of historical scans so dashboards are not empty."""
    if os.getenv("BRANDGUARD_SEED_DEMO", "1") == "0":
        return 0

    from .pipeline import run_inspection, serialize_scan  # local import avoids cycle

    with db.get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"]
    if existing:
        return 0

    created_count = 0
    for index, demo in enumerate(DEMO_SCANS):
        scan_id = f"scan-demo-{index + 1:02d}"
        created_at = (
            datetime.now(timezone.utc) - timedelta(days=demo["days_ago"], hours=3)
        ).isoformat(timespec="seconds")
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
                    "Dhanraj Sonar",
                    demo["title"],
                    demo["content"],
                    demo["channel"],
                    demo["audience"],
                    demo["region"],
                    "Q4 Global Launch",
                    created_at,
                    created_at,
                ),
            )
        run_inspection(scan_id, created_at=created_at)
        # Deterministic overrides so "Guideline Clarity" has real signal.
        with db.get_db() as conn:
            unresolved = conn.execute(
                "SELECT id FROM findings WHERE scan_id = ? AND status = 'Unresolved' "
                "ORDER BY created_at, id",
                (scan_id,),
            ).fetchall()
            if unresolved and index % 2 == 0:
                target = unresolved[-1]["id"]
                resolved_at = (
                    datetime.fromisoformat(created_at) + timedelta(minutes=3 + index * 1.5)
                ).isoformat(timespec="seconds")
                conn.execute(
                    "UPDATE findings SET status='Overridden', resolution_note=?, "
                    "resolved_by='Brand Manager', resolved_at=? WHERE id=?",
                    ("Agency pre-approved exception for this campaign.", resolved_at, target),
                )
        # Refresh the stored score/status now that the seed override is in place.
        run_inspection(scan_id)
        if index == 3:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE scans SET status = 'Published' WHERE id = ?",
                    (scan_id,),
                )
        created_count += 1
    return created_count


def seed_all() -> dict:
    guidelines = seed_guidelines()
    scans = seed_demo_scans()
    return {"guidelines": guidelines, "demo_scans": scans}
