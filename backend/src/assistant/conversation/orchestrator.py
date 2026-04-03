from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings
from assistant.conversation.prompt_builder import build_prompt
from assistant.conversation.schemas import ChatResponse, ChatRequest, SourceAttribution
from assistant.conversation.session import append_message, get_history, get_or_create_session
from assistant.policy.guard import PolicyContext, evaluate as policy_evaluate
from assistant.retrieval import service as retrieval_service
from assistant.routing import router as model_router


async def respond(
    session: AsyncSession,
    request: ChatRequest,
    settings: Settings,
) -> ChatResponse:
    """Process a chat request end-to-end."""
    session_id = await get_or_create_session(session, request.session_id)

    # Retrieve relevant context
    retrieval_result = await retrieval_service.query(session, request.message, top_k=5)
    context_items = retrieval_result.items

    # Get conversation history
    history = await get_history(session, session_id)

    # Build prompt
    prompt = build_prompt(request.message, history, context_items)

    # Policy check
    policy_ctx = PolicyContext(source_type="conversation", consent_granted=True)
    policy_decision = await policy_evaluate(prompt, policy_ctx)

    # Route to model
    model_response = await model_router.invoke(
        prompt=prompt,
        policy_decision=policy_decision,
        settings=settings,
    )

    # Persist messages
    await append_message(session, session_id, "user", request.message)
    await append_message(session, session_id, "assistant", model_response.text)

    grounded = len(context_items) > 0

    sources = [
        SourceAttribution(
            memory_id=item.source.memory_id,
            source_type=item.source.source_type,
            title=item.source.title,
            snippet=item.source.snippet,
            created_at=item.source.created_at,
        )
        for item in context_items
    ]

    return ChatResponse(
        response=model_response.text,
        sources=sources,
        session_id=session_id,
        model_used=model_response.model_used,
        grounded=grounded,
    )
