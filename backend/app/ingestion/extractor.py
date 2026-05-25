from dataclasses import dataclass, field
import io

import fitz  # PyMuPDF


@dataclass
class PageData:
    page_number: int
    text: str
    blocks: list[dict] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    filename: str
    pages: list[PageData]
    total_pages: int
    metadata: dict = field(default_factory=dict)


def extract_text(file_bytes: bytes, filename: str = "document.pdf") -> ExtractedDocument:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[PageData] = []
    metadata: dict = dict(doc.metadata) if doc.metadata else {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        block_data = [
            {
                "bbox": list(b[:4]),
                "text": b[4].strip() if len(b) > 4 else "",
                "block_type": b[5] if len(b) > 5 else 0,
            }
            for b in blocks
        ]
        pages.append(PageData(
            page_number=page_num + 1,
            text=page.get_text("text"),
            blocks=block_data,
        ))

    doc.close()
    return ExtractedDocument(
        filename=filename,
        pages=pages,
        total_pages=len(pages),
        metadata={"page_count": len(pages), **metadata},
    )


def _estimate_heading_level(block: dict, font_sizes_on_page: list[float]) -> int:
    font_size = block.get("font_size", 0)
    if not font_size or not font_sizes_on_page:
        return 0
    avg = sum(font_sizes_on_page) / len(font_sizes_on_page)
    if font_size >= avg * 1.3:
        return 2
    if font_size >= avg * 1.1:
        return 3
    return 0
