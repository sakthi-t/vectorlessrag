from app.retrieval.bm25 import BM25Result


def fuse_and_rank(
    results: list[BM25Result],
    top_k: int = 5,
) -> list[BM25Result]:
    seen_ids: set[str] = set()
    deduped: list[BM25Result] = []

    for r in sorted(results, key=lambda x: x.score, reverse=True):
        content_key = r.content[:100].strip().lower()
        if content_key not in seen_ids:
            seen_ids.add(content_key)
            deduped.append(r)

    deduped.sort(key=lambda r: r.score, reverse=True)
    return deduped[:top_k]


def build_citations(
    results: list[BM25Result],
) -> list[dict]:
    citations: list[dict] = []
    seen_pages: set[int] = set()

    for r in results:
        if r.page_number not in seen_pages:
            seen_pages.add(r.page_number)
            citations.append({
                "chunk_id": str(r.chunk_id),
                "page_number": r.page_number,
                "heading_path": r.heading_path,
                "relevance_score": round(r.score, 4),
            })

    citations.sort(key=lambda c: c["page_number"])
    return citations


def format_context_for_llm(results: list[BM25Result]) -> str:
    parts: list[str] = []
    for i, r in enumerate(results):
        heading = " > ".join(r.heading_path) if r.heading_path else "Unknown Section"
        parts.append(
            f"[Source {i + 1}] (Page {r.page_number}, {heading})\n{r.content.strip()}"
        )
    return "\n\n---\n\n".join(parts)
