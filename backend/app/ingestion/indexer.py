import uuid
import math
import re
from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunker import Chunk
from app.models.bm25_index import BM25Stats


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "not", "no", "nor",
    "so", "if", "then", "else", "when", "where", "why", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "this", "that", "these", "those",
    "it", "its", "he", "she", "they", "them", "we", "us", "you", "your",
    "me", "my", "our", "their", "about", "above", "after", "again",
    "into", "through", "during", "before", "between", "under", "over",
    "up", "down", "out", "off", "just", "very", "too", "also", "now",
    "here", "there", "which", "who", "whom",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _compute_bm25_stats(chunks: list[Chunk]) -> list[dict]:
    total_chunks = len(chunks)
    if total_chunks == 0:
        return []

    # Per-chunk term frequencies
    chunk_term_counts: list[Counter] = []
    for chunk in chunks:
        tokens = _tokenize(chunk.content)
        chunk_term_counts.append(Counter(tokens))

    # Document frequency: how many chunks contain each term
    doc_freq: Counter = Counter()
    for term_counter in chunk_term_counts:
        doc_freq.update(term_counter.keys())

    # IDF score for each term
    idf_scores: dict[str, float] = {}
    for term, df in doc_freq.items():
        idf_scores[term] = math.log((total_chunks - df + 0.5) / (df + 0.5) + 1.0)

    return [
        {"term": term, "doc_frequency": df, "idf_score": round(idf_scores[term], 6)}
        for term, df in doc_freq.items()
    ]


async def build_bm25_index(
    db: AsyncSession,
    chunks: list[Chunk],
    document_id: uuid.UUID,
    tenant_id: str,
    chunk_ids: list[uuid.UUID],
) -> None:
    # Populate search_vector for each chunk using tsvector
    for chunk_id, chunk in zip(chunk_ids, chunks):
        await db.execute(
            text(
                "UPDATE chunks SET search_vector = to_tsvector('english', :content) WHERE id = :id"
            ),
            {"content": chunk.content, "id": str(chunk_id)},
        )

    # Compute and store BM25 statistics
    stats_entries = _compute_bm25_stats(chunks)
    batch_size = 500
    for i in range(0, len(stats_entries), batch_size):
        batch = stats_entries[i : i + batch_size]
        db.add_all([
            BM25Stats(
                document_id=document_id,
                tenant_id=tenant_id,
                term=e["term"],
                doc_frequency=e["doc_frequency"],
                idf_score=e["idf_score"],
            )
            for e in batch
        ])
        await db.flush()

    await db.commit()
