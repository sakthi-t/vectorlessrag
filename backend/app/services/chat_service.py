import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from app.config import settings
from app.models.chat import ChatMessage
from app.retrieval.engine import retrieval_engine, RetrievalResult
from app.retrieval.evaluator import evaluate_answer

CONTEXT_WINDOW = 10
CACHE_WINDOW = 20
CACHE_SIMILARITY_THRESHOLD = 0.6


CHAT_SYSTEM_PROMPT = """You are a helpful document assistant. Answer the user's question using ONLY the provided document excerpts below.
Follow these rules strictly:

1. Base your answer ONLY on the provided document excerpts. Do not use outside knowledge.
2. Cite sources inline using the format [Page N] where N is the page number from the source metadata.
3. If the provided excerpts do not contain enough information to answer the question, say: "I couldn't find relevant information about that in the document."
4. Be concise and direct. Use bullet points for lists.
5. Do not make up information, guess, or speculate beyond what the excerpts contain.
6. If the user's question is a follow-up to a previous answer, use the conversation history for context but still ground your answer in the excerpts.

The document excerpts are separated by "---" markers. Each excerpt begins with a [Source] header showing the page number and section."""


RELEVANCE_SYSTEM_PROMPT = """You are a document relevance classifier. Your job is to determine if a user's question is likely answerable from a document.

Analyze the user's message and answer ONLY with "RELEVANT" or "NOT_RELEVANT".

A question is RELEVANT if:
- It asks about the document's content, topics, data, findings, or information
- It's a follow-up clarification to a previous conversation about the document
- It asks for summaries, analysis, or extraction of information from the document

A question is NOT_RELEVANT if:
- It's a generic greeting or small talk
- It asks about topics completely unrelated to the document
- It's a test of general knowledge (e.g., "What is the capital of France?")
- It's asking the AI to write code, create content, or perform tasks unrelated to the document
- It's asking about the AI itself or its capabilities

Answer ONLY with "RELEVANT" or "NOT_RELEVANT"."""


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def _hash_query(query: str) -> str:
    return hashlib.sha256(_normalize_query(query).encode()).hexdigest()


async def _load_recent_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
    limit: int = CONTEXT_WINDOW,
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


def _messages_to_langchain(messages: list[ChatMessage]) -> list[BaseMessage]:
    lc_messages: list[BaseMessage] = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


async def _find_cached_answer(
    db: AsyncSession,
    session_id: uuid.UUID,
    query: str,
) -> ChatMessage | None:
    normalized_query = _normalize_query(query)

    result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "assistant",
            ChatMessage.from_cache.is_(False),
        ).order_by(ChatMessage.created_at.desc()).limit(CACHE_WINDOW)
    )

    for msg in result.scalars().all():
        if msg.content and _jaccard_similarity(normalized_query, _normalize_query(msg.content)) > CACHE_SIMILARITY_THRESHOLD:
            return msg

    return None


async def _check_relevance(
    query: str,
    conversation_history: list[BaseMessage],
) -> bool:
    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=10,
    )
    messages: list[BaseMessage] = [SystemMessage(content=RELEVANCE_SYSTEM_PROMPT)]

    if len(conversation_history) > 0:
        context_summary = "\n".join(
            [f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content[:200]}"
             for m in conversation_history[-4:]]
        )
        messages.append(SystemMessage(
            content=f"Previous conversation context:\n{context_summary}"
        ))

    messages.append(HumanMessage(content=f"User question: {query}"))

    response = await llm.ainvoke(messages)
    result = response.content.strip().upper() if isinstance(response.content, str) else ""
    return "RELEVANT" in result


async def _generate_llm_response(
    query: str,
    conversation_history: list[BaseMessage],
    retrieval_result: RetrievalResult,
) -> str:
    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        max_tokens=1024,
    )

    messages: list[BaseMessage] = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    if retrieval_result.context_text:
        context_with_excerpts = (
            f"DOCUMENT EXCERPTS:\n\n{retrieval_result.context_text}\n\n"
            f"Use the excerpts above to answer the user's question."
        )
        messages.append(SystemMessage(content=context_with_excerpts))

    if conversation_history:
        messages.extend(conversation_history[-CONTEXT_WINDOW:])

    messages.append(HumanMessage(content=query))

    response = await llm.ainvoke(messages)
    return response.content if isinstance(response.content, str) else ""


class ChatService:
    async def handle_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_message_content: str,
        document_id: uuid.UUID,
        tenant_id: str,
    ) -> ChatMessage:
        # 1. Store the user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message_content,
            citations={},
            retrieval_metadata={},
        )
        db.add(user_msg)
        await db.flush()

        # 2. Load conversation history
        recent_messages = await _load_recent_messages(db, session_id, limit=CONTEXT_WINDOW)
        conversation_history = _messages_to_langchain(recent_messages)

        # 3. Check cache-hit
        cached = await _find_cached_answer(db, session_id, user_message_content)
        if cached:
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=cached.content,
                citations=cached.citations or {},
                retrieval_metadata=cached.retrieval_metadata or {},
                from_cache=True,
                token_count=cached.token_count,
                evaluation=cached.evaluation,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 4. Check relevance
        is_relevant = await _check_relevance(user_message_content, conversation_history)

        if not is_relevant:
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content="I'm designed to answer questions about the uploaded document. "
                        "It looks like your question isn't related to the document content. "
                        "Could you ask something about the document instead?",
                citations={},
                retrieval_metadata={"relevance_check": False},
                from_cache=False,
                evaluation={
                    "faithfulness": 0,
                    "groundedness": 0,
                    "citation_accuracy": 0,
                    "relevance": 0,
                },
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 5. Run retrieval
        retrieval_result = await retrieval_engine.retrieve(
            db=db,
            query=user_message_content,
            document_id=document_id,
            tenant_id=tenant_id,
        )

        # 6. If no results found, respond without hallucination
        if not retrieval_result.has_results:
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content="I searched the document but couldn't find relevant information "
                        "to answer your question. Could you try rephrasing, or ask about "
                        "a different aspect of the document?",
                citations={},
                retrieval_metadata={"searched": True, "results_found": 0},
                from_cache=False,
                evaluation={
                    "faithfulness": 0,
                    "groundedness": 0,
                    "citation_accuracy": 0,
                    "relevance": 0,
                },
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 7. Generate LLM response with context
        llm_response = await _generate_llm_response(
            query=user_message_content,
            conversation_history=conversation_history,
            retrieval_result=retrieval_result,
        )

        token_count = len(llm_response.split()) if llm_response else 0

        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=llm_response,
            citations=retrieval_result.citations,
            retrieval_metadata={
                "searched": True,
                "results_found": retrieval_result.result_count,
                "bm25_used": retrieval_result.bm25_used,
                "low_confidence": retrieval_result.low_confidence,
                "strategy": "bm25",
            },
            from_cache=False,
            token_count=token_count,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        # 8. Run LLM judge evaluation (GPT-4o) — stores scores on the same message
        try:
            scores = await evaluate_answer(
                query=user_message_content,
                answer=llm_response,
                retrieval_result=retrieval_result,
            )
            if scores:
                assistant_msg.evaluation = {
                    "faithfulness": scores.get("faithfulness", 0),
                    "groundedness": scores.get("groundedness", 0),
                    "citation_accuracy": scores.get("citation_accuracy", 0),
                    "relevance": scores.get("relevance", 0),
                }
                await db.commit()
                await db.refresh(assistant_msg)
        except Exception:
            pass

        return assistant_msg


chat_service = ChatService()
