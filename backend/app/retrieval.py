"""Lightweight retrieval over the brand knowledge base.

The demo ships a TF-IDF cosine ranker so semantic-style search works with zero
external services.  `search()` is the single integration point: swap the scoring
body for pgvector (`embedding <=> query_embedding`) or an embedding API and the
rest of the app keeps working.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from . import db

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "be", "as", "at", "by", "it", "this", "that", "our", "we", "you",
    "your", "must", "may", "not", "any", "all", "from", "use", "used",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _index(rows: list[dict]) -> tuple[list[Counter], dict[str, float]]:
    docs = [
        Counter(tokenize(f"{r['title']} {r['section']} {r['content']} {r['tags']}"))
        for r in rows
    ]
    df: Counter = Counter()
    for doc in docs:
        df.update(set(doc))
    n = max(len(rows), 1)
    idf = {term: math.log((n + 1) / (freq + 0.5)) + 1.0 for term, freq in df.items()}
    return docs, idf


def _vector(doc: Counter, idf: dict[str, float]) -> dict[str, float]:
    vec = {term: count * idf.get(term, 1.0) for term, count in doc.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {term: value / norm for term, value in vec.items()}


def search(query: str, limit: int = 5, category: str | None = None) -> list[dict]:
    with db.get_db() as conn:
        sql = "SELECT * FROM guidelines"
        params: list = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

    if not rows or not query.strip():
        return [dict(r, score=0.0) for r in rows[:limit]]

    docs, idf = _index(rows)
    query_vec = _vector(Counter(tokenize(query)), idf)
    scored = []
    for row, doc in zip(rows, docs):
        vec = _vector(doc, idf)
        score = sum(query_vec.get(term, 0.0) * weight for term, weight in vec.items())
        scored.append(dict(row, score=round(score, 4)))

    scored.sort(key=lambda item: item["score"], reverse=True)
    return [item for item in scored[:limit] if item["score"] > 0] or scored[:limit]


def stats() -> dict:
    with db.get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM guidelines").fetchone()["n"]
        by_category = {
            row["category"]: row["n"]
            for row in conn.execute(
                "SELECT category, COUNT(*) AS n FROM guidelines GROUP BY category"
            ).fetchall()
        }
    return {"total_chunks": total, "by_category": by_category}
