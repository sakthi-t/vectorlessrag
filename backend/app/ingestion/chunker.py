import re
from dataclasses import dataclass, field

from .extractor import ExtractedDocument, PageData


@dataclass
class TextBlock:
    text: str
    heading_level: int = 0
    page_start: int = 1
    page_end: int = 1


@dataclass
class Section:
    heading: str
    level: int
    blocks: list[TextBlock] = field(default_factory=list)
    page_start: int = 1
    page_end: int = 1

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text.strip())


@dataclass
class Chunk:
    content: str
    page_number: int
    heading_path: list[str]
    chunk_index: int


def _detect_headings(pages: list[PageData]) -> list[dict]:
    """Detect likely headings by analyzing font sizes across the document."""
    all_font_sizes: list[float] = []
    all_blocks: list[dict] = []
    for page in pages:
        for block in page.blocks:
            if block.get("text"):
                all_blocks.append(block)

    for block in all_blocks:
        # Estimate font size from block height as proxy
        bbox = block.get("bbox", [0, 0, 0, 0])
        if len(bbox) >= 4:
            block_height = bbox[3] - bbox[1]
            if block_height > 5:
                all_font_sizes.append(block_height)

    if not all_font_sizes:
        return []

    avg_height = sum(all_font_sizes) / len(all_font_sizes)

    headings = []
    for block in all_blocks:
        bbox = block.get("bbox", [0, 0, 0, 0])
        block_height = bbox[3] - bbox[1] if len(bbox) >= 4 else 0

        text = block.get("text", "").strip()
        if not text:
            continue

        # Heuristic: short text + larger font = heading
        is_short = len(text) < 120
        is_larger = block_height >= avg_height * 1.15

        if is_short and is_larger:
            level = 1 if block_height >= avg_height * 1.5 else 2
            headings.append({"text": text, "level": level, "bbox": bbox, "page": block.get("page", 1)})

    return headings


def chunk_document(extracted: ExtractedDocument, max_chunk_chars: int = 1500) -> list[Chunk]:
    pages = extracted.pages
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        paragraphs = _split_paragraphs(page_text)
        current_chunk_parts: list[str] = []
        current_chunk_len = 0

        heading = _guess_top_heading(paragraphs)

        for para in paragraphs:
            para_len = len(para)
            if current_chunk_len + para_len > max_chunk_chars and current_chunk_parts:
                chunks.append(Chunk(
                    content="\n".join(current_chunk_parts),
                    page_number=page.page_number,
                    heading_path=[heading] if heading else [],
                    chunk_index=chunk_index,
                ))
                chunk_index += 1
                current_chunk_parts = [para]
                current_chunk_len = para_len
            else:
                current_chunk_parts.append(para)
                current_chunk_len += para_len

        if current_chunk_parts:
            chunks.append(Chunk(
                content="\n".join(current_chunk_parts),
                page_number=page.page_number,
                heading_path=[heading] if heading else [],
                chunk_index=chunk_index,
            ))
            chunk_index += 1

    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double newlines or single newlines."""
    raw = re.split(r"\n\s*\n", text)
    result = []
    for para in raw:
        stripped = para.strip()
        if stripped:
            lines = stripped.split("\n")
            for line in lines:
                ls = line.strip()
                if ls:
                    result.append(ls)
    return result


def _guess_top_heading(paragraphs: list[str]) -> str:
    """Heuristic: first short non-empty line that looks like a heading."""
    for para in paragraphs[:5]:
        clean = para.strip()
        if 3 < len(clean) < 100 and not clean.endswith("."):
            return clean
    return ""
