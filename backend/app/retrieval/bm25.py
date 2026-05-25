import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# BM25 parameters
K1 = 1.5
B = 0.75
TOP_K = 20


@dataclass
class BM25Result:
    chunk_id: uuid.UUID
    content: str
    score: float
    page_number: int
    heading_path: list[str]
    document_id: uuid.UUID


@dataclass
class BM25SearchResults:
    results: list[BM25Result] = field(default_factory=list)
    max_score: float = 0.0

    @property
    def has_good_results(self) -> bool:
        return self.max_score >= CONFIDENCE_THRESHOLD

    @property
    def has_any_results(self) -> bool:
        return len(self.results) > 0


CONFIDENCE_THRESHOLD = 0.5

STOP_WORDS: set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "has", "had", "he", "her", "him", "his", "how", "i",
    "in", "is", "it", "its", "me", "my", "not", "of", "on", "or", "our",
    "she", "that", "the", "their", "them", "they", "this", "to", "was",
    "we", "were", "what", "when", "where", "which", "who", "will", "with",
    "would", "you", "your",
}


def _tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in re.findall(r"[a-zA-Z0-9]+", text)
        if t.lower() not in STOP_WORDS and len(t) > 1
    ]


def _word_count(text: str, token: str) -> int:
    """Count token occurrences using word boundaries, not substrings."""
    return len(re.findall(r'\b' + re.escape(token) + r'\b', text.lower()))


def _bm25_tf_score(token_count: int, doc_len: float, avg_doc_len: float) -> float:
    tf = token_count / max(doc_len, 1)
    numerator = tf * (K1 + 1)
    denominator = tf + K1 * (1 - B + B * (doc_len / max(avg_doc_len, 1)))
    return numerator / denominator if denominator > 0 else 0.0


async def search(
    db: AsyncSession,
    query: str,
    document_id: uuid.UUID,
    tenant_id: str,
    top_k: int = TOP_K,
) -> BM25SearchResults:
    tokens = _tokenize(query)
    if not tokens:
        return BM25SearchResults()

    idf_lookup: dict[str, float] = {}
    idf_result = await db.execute(
        text("""
            SELECT term, idf_score
            FROM bm25_stats
            WHERE tenant_id = :tenant_id
              AND document_id = :document_id
              AND term = ANY(:terms)
        """),
        {"tenant_id": tenant_id, "document_id": document_id, "terms": tokens},
    )
    for row in idf_result:
        idf_lookup[row[0]] = row[1]

    default_idf = 0.5

    avg_len_result = await db.execute(
        text("""
            SELECT COALESCE(AVG(char_length(content)), 1)
            FROM chunks
            WHERE tenant_id = :tenant_id AND document_id = :document_id
        """),
        {"tenant_id": tenant_id, "document_id": document_id},
    )
    avg_doc_len = float(avg_len_result.scalar() or 1)

    results_by_id: dict[uuid.UUID, BM25Result] = {}
    max_score = 0.0

    def _merge_result(chunk_id, content, doc_len, meta, page_num, heading, bm25_score, fts_rank=0.0):
        nonlocal max_score
        first_line = content[:120].lower()
        first_line_matches = sum(1 for t in tokens if _word_count(first_line, t) > 0)
        if first_line_matches > 0:
            bm25_score *= (1 + first_line_matches * 10)

        combined = (bm25_score * 0.7) + (fts_rank * 0.3)
        max_score = max(max_score, combined)

        existing = results_by_id.get(chunk_id)
        if existing is None or combined > existing.score:
            results_by_id[chunk_id] = BM25Result(
                chunk_id=chunk_id, content=content, score=combined,
                page_number=page_num, heading_path=heading if isinstance(heading, list) else [],
                document_id=document_id,
            )

    # 1. FTS search
    fts_rows = await db.execute(
        text("""
            SELECT c.id, c.content, c.metadata,
                   ts_rank_cd(c.search_vector, websearch_to_tsquery('english', :query), 32) AS fts_rank,
                   char_length(c.content) AS doc_len
            FROM chunks c
            WHERE c.tenant_id = :tenant_id
              AND c.document_id = :document_id
              AND c.search_vector @@ websearch_to_tsquery('english', :query)
            ORDER BY fts_rank DESC
            LIMIT :limit
        """),
        {"tenant_id": tenant_id, "document_id": document_id, "query": query, "limit": top_k},
    )

    for row in fts_rows:
        chunk_id, content, metadata_val, fts_rank, doc_len = row
        doc_len = float(doc_len) if doc_len else 1.0
        meta = metadata_val or {}
        bm25_score = sum(
            idf_lookup.get(t, default_idf) * _bm25_tf_score(_word_count(content, t), doc_len, avg_doc_len)
            for t in tokens
        )
        _merge_result(
            chunk_id, content, doc_len, meta,
            meta.get("page_number", 1), meta.get("heading_path", []),
            bm25_score, float(fts_rank),
        )

    # 2. ILIKE search (density-based: how many query tokens appear in the chunk)
    for token in tokens:
        ilike_rows = await db.execute(
            text("""
                SELECT c.id, c.content, c.metadata, char_length(c.content) AS doc_len
                FROM chunks c
                WHERE c.tenant_id = :tenant_id
                  AND c.document_id = :document_id
                  AND c.content ILIKE :pattern
                LIMIT :limit
            """),
            {"tenant_id": tenant_id, "document_id": document_id, "pattern": f"%{token}%", "limit": top_k},
        )
        for row in ilike_rows:
            chunk_id, content, metadata_val, doc_len = row
            doc_len = float(doc_len) if doc_len else 1.0
            meta = metadata_val or {}

            # Score: how many of the query tokens appear in this chunk?
            # Require at least half the tokens to match, with minimum of 2 for multi-token queries
            matched_tokens = sum(1 for t in tokens if _word_count(content, t) > 0)
            total_tokens = len(tokens)
            min_required = min(2, max(1, total_tokens // 2)) if total_tokens > 1 else 1
            if matched_tokens < min_required:
                continue
            bm25_score = matched_tokens / total_tokens

            _merge_result(
                chunk_id, content, doc_len, meta,
                meta.get("page_number", 1), meta.get("heading_path", []),
                bm25_score, 0.0,
            )

    results = sorted(results_by_id.values(), key=lambda r: r.score, reverse=True)
    return BM25SearchResults(results=results[:top_k], max_score=max_score)
