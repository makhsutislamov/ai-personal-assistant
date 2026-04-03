from __future__ import annotations

import json

from assistant.config import Settings
from assistant.policy.guard import PolicyContext
from assistant.policy.guard import evaluate as policy_evaluate
from assistant.routing import router as model_router
from assistant.tasks.schemas import TaskIntent

_INTENT_PROMPT = """\
Extract task intent from the user message below. Return JSON with these keys:
- objective: what needs to be done (string)
- due_context: any due date or time hint (string or null)
- impact_level: "high" if this action is destructive/irreversible/high-stakes, else "normal"

User message: {message}

Respond with ONLY valid JSON, no markdown.
"""


async def parse_task_intent(message: str, settings: Settings) -> TaskIntent | None:
    """Use the model to extract task intent from a user message."""
    prompt = _INTENT_PROMPT.format(message=message)

    # Check for obvious task keywords — skip if message seems non-task
    task_keywords = [
        "please", "could you", "can you", "do", "complete", "finish",
        "task", "remind", "schedule", "create", "send", "update", "fix",
    ]
    if not any(kw in message.lower() for kw in task_keywords):
        return None

    policy_ctx = PolicyContext(source_type="conversation", consent_granted=True)
    policy_decision = await policy_evaluate(prompt, policy_ctx)

    model_response = await model_router.invoke(
        prompt=prompt,
        policy_decision=policy_decision,
        settings=settings,
    )

    import re
    raw = model_response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    try:
        data = json.loads(raw.strip())
        return TaskIntent(
            objective=data.get("objective", message),
            due_context=data.get("due_context"),
            impact_level=data.get("impact_level", "normal"),
        )
    except (json.JSONDecodeError, KeyError):
        return None
