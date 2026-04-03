from __future__ import annotations

import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings
from assistant.conversation.session import get_history
from assistant.notes.schemas import GeneratedNotes
from assistant.policy.guard import PolicyContext, evaluate as policy_evaluate
from assistant.routing import router as model_router

_NOTES_PROMPT = """\
You are a note-taking assistant. Given the conversation transcript below, produce structured notes in JSON format with these exact keys:
- summary: a concise paragraph summarizing the conversation
- decisions: a list of decisions made (may be empty)
- action_items: a list of tasks or follow-ups mentioned (may be empty)
- open_questions: a list of unresolved questions (may be empty)
- suggested_tags: a list of 1-4 topic tags (e.g. ["work", "project-x"])

Respond with ONLY valid JSON, no markdown fences.

Conversation:
{transcript}
"""


def _parse_notes(raw: str) -> GeneratedNotes:
    """Parse model output into GeneratedNotes. Falls back gracefully."""
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        # Return partial notes if JSON parsing fails
        return GeneratedNotes(
            summary=raw[:500],
            decisions=[],
            action_items=[],
            open_questions=[],
            suggested_tags=[],
        )

    return GeneratedNotes(
        summary=data.get("summary", ""),
        decisions=data.get("decisions", []),
        action_items=data.get("action_items", []),
        open_questions=data.get("open_questions", []),
        suggested_tags=data.get("suggested_tags", []),
    )


async def generate_notes(
    session: AsyncSession,
    session_id: str,
    settings: Settings,
) -> GeneratedNotes:
    """Generate structured notes from a conversation session."""
    messages = await get_history(session, session_id)

    if not messages:
        return GeneratedNotes(
            summary="No conversation found.",
            decisions=[],
            action_items=[],
            open_questions=[],
            suggested_tags=[],
        )

    transcript_lines = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        transcript_lines.append(f"{role_label}: {msg.content}")
    transcript = "\n".join(transcript_lines)

    prompt = _NOTES_PROMPT.format(transcript=transcript)

    policy_ctx = PolicyContext(source_type="conversation", consent_granted=True)
    policy_decision = await policy_evaluate(prompt, policy_ctx)

    model_response = await model_router.invoke(
        prompt=prompt,
        policy_decision=policy_decision,
        settings=settings,
    )

    return _parse_notes(model_response.text)
