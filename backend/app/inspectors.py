"""Deterministic multi-agent inspection engine.

Four specialist agents run in parallel over a draft and emit structured drafts
that the pipeline joins to guideline clauses:

    Tone & Vocabulary  -> hype words, superlatives, lexicon, readability
    Fact & Claims      -> percentages, multipliers, guarantees, pricing, recency
    Visual Compliance  -> logo rules, palette, approved imagery
    Accessibility      -> alt text, contrast, link purpose

The rules are intentionally transparent and offline so the hackathon demo is
reproducible.  Each agent is a pure function of (content, context), which makes
it trivial to replace with an LLM/JSON-schema call later - the output contract
stays identical.
"""

from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BRAND_PALETTE = {
    "#0B1F3A": "Ink Navy",
    "#2F6BFF": "Signal Blue",
    "#F5B700": "Spark Amber",
    "#FFFFFF": "White",
}

SEVERITY_WEIGHT = {"Critical": 10, "Warning": 3, "Info": 1}
SEVERITY_ORDER = {"Critical": 0, "Warning": 1, "Info": 2}

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
APPROVED_CUSTOMER_COUNT = "18,400"
CURRENT_YEAR = 2026


def _snippet(content: str, start: int, end: int, padding: int = 0) -> str:
    return content[max(0, start - padding) : min(len(content), end + padding)]


def _draft(
    *,
    agent: str,
    code: str,
    issue_type: str,
    severity: str,
    content: str,
    start: int,
    end: int,
    explanation: str,
    suggested_fix: str | None = None,
) -> dict[str, Any]:
    return {
        "agent": agent,
        "code": code,
        "issue_type": issue_type,
        "severity": severity,
        "offending_segment": content[start:end],
        "start_index": start,
        "end_index": end,
        "explanation": explanation,
        "suggested_fix": suggested_fix,
    }


def _first(pattern: str, content: str, flags: int = 0) -> re.Match | None:
    return re.search(pattern, content, flags)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _relative_luminance(value: str) -> float:
    channels = []
    for channel in _hex_to_rgb(value):
        srgb = channel / 255.0
        channels.append(srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _nearest_palette(value: str) -> str:
    rgb = _hex_to_rgb(value)
    best = min(
        BRAND_PALETTE,
        key=lambda hex_value: sum(
            (a - b) ** 2 for a, b in zip(rgb, _hex_to_rgb(hex_value))
        ),
    )
    return best


def _syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    vowels = "aeiouy"
    count, previous = 0, False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not previous:
            count += 1
        previous = is_vowel
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ee")):
        count -= 1
    return max(1, count)


def flesch_kincaid_grade(text: str) -> float:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    if not words or not sentences:
        return 0.0
    syllables = sum(_syllables(word) for word in words)
    return round(
        0.39 * (len(words) / len(sentences))
        + 11.8 * (syllables / len(words))
        - 15.59,
        1,
    )


# ---------------------------------------------------------------------------
# 1. Tone & Vocabulary agent
# ---------------------------------------------------------------------------

HYPE_TERMS = {
    "revolutionary": "groundbreaking",
    "game-changing": "transformative",
    "world-class": "high-performing",
    "best-in-class": "proven",
    "cutting-edge": "modern",
    "synergy": "collaboration",
    "cheap": "affordable",
    "fast": "quick",
}

SUPERLATIVES = {
    "industry leader": "a recognised enterprise vendor",
    "#1": "a leading",
    "world's best": "a strong",
    "unbeatable": "competitive",
}

LEXICON = {
    "users": "customers",
    "tool": "workspace",
}


def inspect_tone(content: str, ctx: dict) -> list[dict]:
    findings: list[dict] = []

    for term, replacement in HYPE_TERMS.items():
        match = _first(rf"\b{re.escape(term)}\b", content, re.IGNORECASE)
        if not match:
            continue
        findings.append(
            _draft(
                agent="tone",
                code="TONE-2.1",
                issue_type="Hype vocabulary",
                severity="Warning",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"'{match.group(0)}' is on the brand hype-word list. §2.1 asks for "
                    "confident, concrete language instead of unverifiable adjectives."
                ),
                suggested_fix=replacement,
            )
        )

    for phrase, replacement in SUPERLATIVES.items():
        match = _first(rf"\b{re.escape(phrase)}\b", content, re.IGNORECASE)
        if not match:
            continue
        findings.append(
            _draft(
                agent="tone",
                code="TONE-2.2",
                issue_type="Unsupported leadership claim",
                severity="Info",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"'{match.group(0)}' is a leadership claim. It is permitted only when a "
                    "current third-party ranking is cited in the same paragraph."
                ),
                suggested_fix=replacement,
            )
        )

    for term, replacement in LEXICON.items():
        match = _first(rf"\b{term}\b", content, re.IGNORECASE)
        if not match:
            continue
        findings.append(
            _draft(
                agent="tone",
                code="LEX-3.2",
                issue_type="Non-approved vocabulary",
                severity="Info",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"Brand Lexicon §3.2 replaces '{term}' with '{replacement}' for consistent "
                    "product vocabulary."
                ),
                suggested_fix=replacement,
            )
        )

    grade = flesch_kincaid_grade(content)
    if grade > 12:
        findings.append(
            {
                "agent": "tone",
                "code": "EDIT-4.1",
                "issue_type": "Reading level too high",
                "severity": "Warning" if grade > 15 else "Info",
                "offending_segment": _snippet(content, 0, min(len(content), 120)),
                "start_index": 0,
                "end_index": min(len(content), 120),
                "explanation": (
                    f"Flesch-Kincaid grade level is {grade}, above the grade 9 target in "
                    "Editorial Style Guide §4.1. Shorten sentences and prefer plain words."
                ),
                "suggested_fix": None,
            }
        )

    return findings


# ---------------------------------------------------------------------------
# 2. Fact & Claim verification agent
# ---------------------------------------------------------------------------

GUARANTEE_RE = r"\b(guaranteed|guarantees?|risk[- ]free|no[- ]risk|100%)\b"
PERCENT_RE = r"(?<![\w.])(\d{1,3}(?:\.\d+)?)\s*%"
MULTIPLIER_RE = r"(?<![\w.])(\d+(?:\.\d+)?)\s*[xX]\b"
CUSTOMER_RE = (
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d{3,})\+?\s*"
    r"(?:(?:[A-Za-z]+\s+){0,3})(customers|clients|teams|companies)\b"
)
PRICING_RE = (
    r"(?:\$\s?\d[\d,]*(?:\.\d+)?|\b\d{1,2}%\s*off|\b(?:save|get)\s+\d{1,2}%\s*(?:off\b)?"
    r"|\b(?:discount|promo code|coupon)\b)"
)
OLD_YEAR_RE = r"\b(20(?:1\d|2[0-4]))\b"


def inspect_claims(content: str, ctx: dict) -> list[dict]:
    findings: list[dict] = []
    lowered = content.lower()
    has_terms = "terms apply" in lowered or (
        "offer ends" in lowered and "expire" in lowered
    )

    match = _first(PERCENT_RE, content)
    if match:
        value = float(match.group(1))
        if value > 150:
            findings.append(
                _draft(
                    agent="claim",
                    code="FACT-4.2",
                    issue_type="Unverified performance claim",
                    severity="Critical",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        f"'{match.group(0)}' exceeds the verified benchmark. Approved Fact "
                        f"Sheet v2.1 §4.2 caps the measured speedup at 150%; §4.5 explicitly "
                        "retires the 500% figure. Replace with the supported metric."
                    ),
                    suggested_fix="up to 150%",
                )
            )

    match = _first(MULTIPLIER_RE, content)
    if match:
        value = float(match.group(1))
        if value >= 3:
            findings.append(
                _draft(
                    agent="claim",
                    code="FACT-4.2",
                    issue_type="Unverified performance claim",
                    severity="Critical",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        f"'{match.group(0)}' implies a {value}x improvement. The only approved "
                        "benchmark is up to 150% (approximately 2.5x) average speedup."
                    ),
                    suggested_fix="up to 2.5x",
                )
            )

    match = _first(GUARANTEE_RE, content, re.IGNORECASE)
    if match:
        findings.append(
            _draft(
                agent="claim",
                code="LEGAL-3.2",
                issue_type="Prohibited guarantee",
                severity="Critical",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"'{match.group(0)}' is a prohibited guarantee under Legal Disclaimer "
                    "Policy §3.2. Describe documented results and add 'results may vary'."
                ),
                suggested_fix="documented results",
            )
        )

    match = _first(CUSTOMER_RE, content, re.IGNORECASE)
    if match:
        stated = match.group(1).rstrip("+")
        if stated.replace(",", "") != APPROVED_CUSTOMER_COUNT.replace(",", ""):
            findings.append(
                _draft(
                    agent="claim",
                    code="FACT-4.6",
                    issue_type="Outdated customer metric",
                    severity="Warning",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        f"'{match.group(0)}' does not match the audited figure. Approved Fact "
                        f"Sheet v2.1 §4.6 requires {APPROVED_CUSTOMER_COUNT} customers as of Q2 2026."
                    ),
                    suggested_fix=f"{APPROVED_CUSTOMER_COUNT} customers",
                )
            )

    match = _first(PRICING_RE, content, re.IGNORECASE)
    if match and not has_terms:
        segment = match.group(0)
        findings.append(
            _draft(
                agent="claim",
                code="LEGAL-3.1",
                issue_type="Promotion missing disclaimer",
                severity="Warning",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"'{segment}' references pricing or a promotion without an expiry date and "
                    "the required 'terms apply' disclaimer (Legal Disclaimer Policy §3.1)."
                ),
                suggested_fix=f"{segment} (terms apply; offer ends 31 Dec 2026)",
            )
        )

    match = _first(OLD_YEAR_RE, content)
    if match and int(match.group(1)) < CURRENT_YEAR - 1:
        findings.append(
            _draft(
                agent="claim",
                code="EDIT-2.4",
                issue_type="Stale dated claim",
                severity="Info",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"The reference to {match.group(1)} is older than the 18-month freshness "
                    "window in Content Freshness Standard §2.4. Refresh or remove the date."
                ),
                suggested_fix=str(CURRENT_YEAR),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 3. Visual compliance agent
# ---------------------------------------------------------------------------

def inspect_visual(content: str, ctx: dict) -> list[dict]:
    findings: list[dict] = []

    for match in IMAGE_RE.finditer(content):
        alt, url = match.group(1), match.group(2)
        haystack = f"{alt} {url}".lower()

        if "logo" in haystack:
            findings.append(
                _draft(
                    agent="visual",
                    code="VIS-1.3",
                    issue_type="Logo clear-space risk",
                    severity="Warning",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        "Logo placement must preserve 1x clear space on all sides and use the "
                        "approved master asset (Visual Identity Manual §1.3). The submitted "
                        "asset is not the approved master file."
                    ),
                    suggested_fix=(
                        f"![{alt or 'Acme Corp logo'}]"
                        "(https://cdn.acme.com/brand/acme-logo-approved.svg)"
                    ),
                )
            )

        if "cdn.acme.com" not in url.lower() and not url.lower().startswith("/"):
            findings.append(
                _draft(
                    agent="visual",
                    code="VIS-2.2",
                    issue_type="Unauthorised imagery",
                    severity="Warning",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        f"The image source '{url}' is outside the approved asset library "
                        "(cdn.acme.com/brand). Replace it with an approved asset (§2.2)."
                    ),
                    suggested_fix=(
                        f"![{alt or 'Acme Flow dashboard'}]"
                        "(https://cdn.acme.com/brand/approved-dashboard.png)"
                    ),
                )
            )

    for match in HEX_RE.finditer(content):
        value = match.group(0).upper()
        if value in BRAND_PALETTE:
            continue
        nearest = _nearest_palette(value)
        findings.append(
            _draft(
                agent="visual",
                code="VIS-1.6",
                issue_type="Off-palette colour",
                severity="Warning",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"{value} is not in the approved palette (Visual Identity Manual §1.6). "
                    f"The closest approved colour is {nearest} ({BRAND_PALETTE[nearest]})."
                ),
                suggested_fix=nearest,
            )
        )

    return findings


# ---------------------------------------------------------------------------
# 4. Accessibility agent
# ---------------------------------------------------------------------------

def inspect_accessibility(content: str, ctx: dict) -> list[dict]:
    findings: list[dict] = []
    mentions_white = "white" in content.lower()

    for match in IMAGE_RE.finditer(content):
        alt = match.group(1).strip()
        word_count = len(alt.split())
        if word_count == 0:
            findings.append(
                _draft(
                    agent="accessibility",
                    code="A11Y-5.2",
                    issue_type="Missing alternative text",
                    severity="Critical",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        "The image has no alternative text. WCAG 2.1 AA §5.2 requires at "
                        "least 5 descriptive words conveying the image's purpose."
                    ),
                    suggested_fix=(
                        "![Acme Flow approval dashboard showing three pending reviews]"
                        f"({match.group(2)})"
                    ),
                )
            )
        elif word_count < 5:
            findings.append(
                _draft(
                    agent="accessibility",
                    code="A11Y-5.2",
                    issue_type="Insufficient alternative text",
                    severity="Warning",
                    content=content,
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        f"Alt text '{alt}' is {word_count} word(s). Accessibility Standard "
                        "§5.2 requires at least 5 descriptive words."
                    ),
                    suggested_fix=(
                        f"![Acme Flow approval dashboard showing {alt}]"
                        f"({match.group(2)})"
                    ),
                )
            )

    if mentions_white:
        for match in HEX_RE.finditer(content):
            value = match.group(0).upper()
            ratio = contrast_ratio(value, "#FFFFFF")
            if ratio < 4.5:
                findings.append(
                    _draft(
                        agent="accessibility",
                        code="A11Y-5.4",
                        issue_type="Insufficient colour contrast",
                        severity="Warning",
                        content=content,
                        start=match.start(),
                        end=match.end(),
                        explanation=(
                            f"{value} on white measures {ratio}:1, below the 4.5:1 WCAG 2.1 AA "
                            "minimum (§5.4). Use Ink Navy #0B1F3A for body text."
                        ),
                        suggested_fix="#0B1F3A",
                    )
                )

    match = _first(r"\b(?:click here|read more|learn more)\b", content, re.IGNORECASE)
    if match:
        findings.append(
            _draft(
                agent="accessibility",
                code="A11Y-5.6",
                issue_type="Ambiguous link text",
                severity="Info",
                content=content,
                start=match.start(),
                end=match.end(),
                explanation=(
                    f"'{match.group(0)}' does not describe the destination. Accessibility "
                    "Standard §5.6 requires descriptive link text."
                ),
                suggested_fix="View the Acme Flow dashboard",
            )
        )

    return findings


AGENTS = {
    "tone": inspect_tone,
    "claim": inspect_claims,
    "visual": inspect_visual,
    "accessibility": inspect_accessibility,
}


def run_agents(content: str, ctx: dict | None = None) -> list[dict]:
    """Run all four inspectors and return de-duplicated drafts."""
    ctx = ctx or {}
    drafts: list[dict] = []
    for inspect in AGENTS.values():
        drafts.extend(inspect(content, ctx))

    seen: set[tuple[str, str, int]] = set()
    unique: list[dict] = []
    for draft in drafts:
        key = (draft["agent"], draft["code"], draft["start_index"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(draft)

    unique.sort(key=lambda d: (SEVERITY_ORDER[d["severity"]], d["start_index"]))
    return unique
