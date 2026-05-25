import asyncio
import uuid
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_pipeline(document_id: str, tenant_id: str) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.session import AsyncSessionLocal
    from app.models.document import Document
    from app.services.storage_service import storage_service
    from app.ingestion.extractor import extract_text
    from app.ingestion.chunker import chunk_document
    from app.ingestion.tree_builder import build_tree, flatten_tree
    from app.retrieval.summarizer import generate_summaries
    from app.ingestion.indexer import build_bm25_index
    from app.models.document_tree import DocumentTree
    from app.models.chunk import Chunk

    doc_uuid = uuid.UUID(document_id)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Document).where(Document.id == doc_uuid, Document.tenant_id == tenant_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                return

            document.status = "processing"
            await db.commit()

            file_bytes = await storage_service.download(document.b2_file_key)
            extracted = extract_text(file_bytes, document.filename)
            chunks = chunk_document(extracted)
            tree_root = build_tree(extracted, chunks, doc_uuid, tenant_id)

            chunks_by_page: dict[int, str] = {}
            for chunk in chunks:
                existing = chunks_by_page.get(chunk.page_number, "")
                chunks_by_page[chunk.page_number] = existing + " " + chunk.content

            tree_root = await generate_summaries(tree_root, chunks_by_page)

            all_tree_nodes = flatten_tree(tree_root)
            db.add_all([
                DocumentTree(
                    id=node.id,
                    document_id=node.document_id,
                    tenant_id=node.tenant_id,
                    parent_node_id=node.parent_node_id,
                    depth=node.depth,
                    node_type=node.node_type,
                    title=node.title,
                    summary=node.summary,
                    start_page=node.start_page,
                    end_page=node.end_page,
                    sibling_order=node.sibling_order,
                )
                for node in all_tree_nodes
            ])
            await db.flush()

            para_to_page: dict[uuid.UUID, int] = {}
            for node in all_tree_nodes:
                if node.node_type == "paragraph":
                    para_to_page[node.id] = node.start_page or 1

            chunk_ids: list[uuid.UUID] = []
            chunk_index = 0
            for page_num in sorted(chunks_by_page.keys()):
                page_para_node_id = None
                for node_id, pn in para_to_page.items():
                    if pn == page_num:
                        page_para_node_id = node_id
                        break

                page_chunks = [c for c in chunks if c.page_number == page_num]
                if not page_chunks:
                    fallback_nodes = [n for n in all_tree_nodes if n.node_type == "paragraph" and n.start_page == page_num]
                    page_para_node_id = fallback_nodes[0].id if fallback_nodes else all_tree_nodes[1].id if len(all_tree_nodes) > 1 else None

                for chunk in page_chunks:
                    chunk_id = uuid.uuid4()
                    chunk_ids.append(chunk_id)
                    db.add(Chunk(
                        id=chunk_id,
                        document_id=doc_uuid,
                        tree_node_id=page_para_node_id,
                        tenant_id=tenant_id,
                        content=chunk.content,
                        chunk_index=chunk_index,
                        chunk_metadata={
                            "page_number": chunk.page_number,
                            "heading_path": chunk.heading_path,
                        },
                    ))
                    chunk_index += 1

            await db.flush()
            await build_bm25_index(db, chunks, doc_uuid, tenant_id, chunk_ids)

            document.status = "ready"
            document.doc_metadata = {
                **document.doc_metadata,
                "page_count": extracted.total_pages,
                "chunk_count": len(chunks),
                "tree_node_count": len(all_tree_nodes),
            }
            await db.commit()

        except Exception:
            await db.rollback()
            async with AsyncSessionLocal() as recovery_db:
                result = await recovery_db.execute(
                    select(Document).where(Document.id == doc_uuid, Document.tenant_id == tenant_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    await recovery_db.commit()
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, tenant_id: str):
    try:
        asyncio.run(_run_pipeline(document_id, tenant_id))
    except Exception as exc:
        raise self.retry(exc=exc)
