import uuid
from dataclasses import dataclass, field

from .extractor import ExtractedDocument
from .chunker import Chunk


@dataclass
class TreeNode:
    id: uuid.UUID
    document_id: uuid.UUID
    tenant_id: str
    parent_node_id: uuid.UUID | None
    depth: int
    node_type: str
    title: str | None
    summary: str | None
    start_page: int | None
    end_page: int | None
    sibling_order: int
    children: list["TreeNode"] = field(default_factory=list)


def build_tree(
    extracted: ExtractedDocument,
    chunks: list[Chunk],
    document_id: uuid.UUID,
    tenant_id: str,
) -> TreeNode:
    root = TreeNode(
        id=uuid.uuid4(),
        document_id=document_id,
        tenant_id=tenant_id,
        parent_node_id=None,
        depth=0,
        node_type="document",
        title=extracted.filename,
        summary=None,
        start_page=1,
        end_page=extracted.total_pages,
        sibling_order=0,
    )

    # Group chunks by page and create page-level section nodes
    page_groups: dict[int, list[Chunk]] = {}
    for chunk in chunks:
        page_groups.setdefault(chunk.page_number, []).append(chunk)

    order = 0
    for page_num, page_chunks in sorted(page_groups.items()):
        page_text = "".join(c.content for c in page_chunks)[:200]
        heading = page_chunks[0].heading_path[0] if page_chunks[0].heading_path else f"Page {page_num}"

        page_node = TreeNode(
            id=uuid.uuid4(),
            document_id=document_id,
            tenant_id=tenant_id,
            parent_node_id=root.id,
            depth=1,
            node_type="page",
            title=heading,
            summary=None,
            start_page=page_num,
            end_page=page_num,
            sibling_order=order,
        )
        order += 1

        # Create paragraph nodes under each page
        para_order = 0
        for chunk in page_chunks:
            para_node = TreeNode(
                id=uuid.uuid4(),
                document_id=document_id,
                tenant_id=tenant_id,
                parent_node_id=page_node.id,
                depth=2,
                node_type="paragraph",
                title=None,
                summary=None,
                start_page=page_num,
                end_page=page_num,
                sibling_order=para_order,
            )
            para_order += 1
            page_node.children.append(para_node)

        root.children.append(page_node)

    return root


def flatten_tree(root: TreeNode) -> list[TreeNode]:
    """Flatten tree into a list for bulk DB insertion."""
    result = [root]
    for child in root.children:
        result.extend(flatten_tree(child))
    return result
