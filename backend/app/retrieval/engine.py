import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.bm25 import search as bm25_search, BM25Result, BM25SearchResults
from app.retrieval.ranker import fuse_and_rank, build_citations, format_context_for_llm


@dataclass
class RetrievalResult:
    chunks: list[BM25Result] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    context_text: str = ""
    bm25_used: bool = False
    low_confidence: bool = False
    result_count: int = 0

    @property
    def has_results(self) -> bool:
        return self.result_count > 0


class RetrievalEngine:
    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        document_id: uuid.UUID,
        tenant_id: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        bm25_results: BM25SearchResults = await bm25_search(
            db=db,
            query=query,
            document_id=document_id,
            tenant_id=tenant_id,
            top_k=max(top_k * 2, 10),
        )

        if not bm25_results.has_any_results:
            return RetrievalResult(
                bm25_used=True,
                low_confidence=True,
                result_count=0,
            )

        fused = fuse_and_rank(bm25_results.results, top_k=top_k)

        citations = build_citations(fused)
        context_text = format_context_for_llm(fused)

        return RetrievalResult(
            chunks=fused,
            citations=citations,
            context_text=context_text,
            bm25_used=True,
            low_confidence=not bm25_results.has_good_results,
            result_count=len(fused),
        )


retrieval_engine = RetrievalEngine()
