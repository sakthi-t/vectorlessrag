import asyncio
from openai import AsyncOpenAI

from app.config import settings
from app.ingestion.tree_builder import TreeNode, flatten_tree

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SUMMARY_BATCH_SIZE = 5
SUMMARY_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a document summarizer. Write a concise 1-2 sentence summary of the provided text.
Focus on key information, facts, and findings. Do not include meta-commentary like "This section discusses..." """


async def _summarize_text(text: str) -> str:
    if not text or len(text.strip()) < 50:
        return text.strip() if text else ""

    try:
        response = await client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text[:3000]},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else ""
    except Exception:
        return text[:200].strip()


async def generate_summaries(root: TreeNode, chunks_text_by_page: dict[int, str]) -> TreeNode:
    all_nodes = flatten_tree(root)
    paragraph_nodes = [n for n in all_nodes if n.node_type == "paragraph"]
    page_nodes = [n for n in all_nodes if n.node_type == "page"]

    # Summarize paragraph nodes in batches
    for i in range(0, len(paragraph_nodes), SUMMARY_BATCH_SIZE):
        batch = paragraph_nodes[i:i + SUMMARY_BATCH_SIZE]
        tasks = []
        for node in batch:
            page_text = chunks_text_by_page.get(node.start_page or 1, "")
            tasks.append(_summarize_text(page_text[:1500]))
        summaries = await asyncio.gather(*tasks)
        for node, summary in zip(batch, summaries):
            if summary:
                node.summary = summary

    # Summarize page nodes by combining child summaries
    for page_node in page_nodes:
        child_summaries = [c.summary for c in page_node.children if c.summary]
        combined = " ".join(child_summaries)[:2000]
        page_node.summary = await _summarize_text(combined) if combined else None

    # Root summary from page summaries
    page_summaries = [s for s in (p.summary for p in page_nodes) if s]
    if page_summaries:
        root.summary = await _summarize_text(" ".join(page_summaries)[:3000])

    return root
