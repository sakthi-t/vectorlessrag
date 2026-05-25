import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.retrieval.engine import RetrievalResult

EVAL_SYSTEM_PROMPT = """You are evaluating a RAG (Retrieval-Augmented Generation) system's response. Your job is to score the answer across four dimensions based solely on whether the answer is grounded in the provided retrieved context.

Return ONLY a valid JSON object with these keys:
{
  "faithfulness": <0-100>,
  "groundedness": <0-100>,
  "citation_accuracy": <0-100>,
  "relevance": <0-100>
}

Scoring rules:
- Compare EVERY factual claim in the answer against the context. Any claim not explicitly present in the context is a hallucination — penalize heavily.
- If the answer contains garbled, truncated, or nonsensical text (repeated words, broken words, corrupted tokens), score faithfulness and groundedness LOW (under 30).
- If the answer refuses to answer (e.g., "I couldn't find information", "I don't know") and the context DOES contain relevant information, score ALL dimensions low (under 20) — the system failed to extract available knowledge.
- If the answer refuses to answer but the context genuinely lacks the information, score all dimensions 0.
- Penalize unsupported claims: any statement not backed by a verbatim match in the context must reduce faithfulness.
- For citation_accuracy: the pages cited must actually contain the information being attributed to them. Mismatches drop this score.
- For relevance: answers that drift from the user's query or introduce unrelated topics score low.
- Faithfulness and groundedness are about word-level and fact-level fidelity to the context. Even if the general topic is correct, fabricated details, garbled tokens, or invented statistics must cause significant score drops.

DO NOT include any text outside the JSON. DO NOT wrap in markdown code blocks."""


REFUSAL_PATTERNS = [
    "i couldn't find",
    "couldn't find relevant information",
    "could not find",
    "no information",
    "does not contain",
    "don't have enough information",
    "i don't see",
    "not mentioned",
    "not covered",
    "i'm designed to answer",
    "it looks like your question",
]


def _is_refusal(answer: str) -> bool:
    lower = answer.lower()
    return any(pattern in lower for pattern in REFUSAL_PATTERNS)


async def evaluate_answer(
    query: str,
    answer: str,
    retrieval_result: RetrievalResult,
) -> dict | None:
    if not retrieval_result or not answer:
        return None

    if _is_refusal(answer):
        return {
            "faithfulness": 0,
            "groundedness": 0,
            "citation_accuracy": 0,
            "relevance": 0,
        }

    if not retrieval_result.context_text:
        return None

    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-4o",
        temperature=0.0,
        max_tokens=200,
    )

    context_truncated = retrieval_result.context_text[:8000]

    messages = [
        SystemMessage(content=EVAL_SYSTEM_PROMPT),
        HumanMessage(content=f"""User Query: {query}

Retrieved Context:
{context_truncated}

Generated Answer: {answer}

Evaluate and return JSON only."""),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else ""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(content)
    except Exception:
        return None
