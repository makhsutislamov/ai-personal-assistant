from __future__ import annotations

from assistant.db.models import ConversationMessage
from assistant.retrieval.schemas import RetrievalItem

_GROUNDING_INSTRUCTION = """
You are a helpful AI assistant with access to the user's personal knowledge base.
When relevant context is provided below, base your response on that context and cite it.
If the retrieved context does not answer the question, say you are uncertain rather than guessing.
"""

_UNCERTAINTY_PROMPT = """
If you cannot answer from the provided context, respond with:
"I don't have enough information about that in my knowledge base. Could you provide more details?"
"""


def build_prompt(
    user_message: str,
    history: list[ConversationMessage],
    context_items: list[RetrievalItem],
) -> str:
    """Assemble the full model prompt."""
    parts: list[str] = [_GROUNDING_INSTRUCTION.strip()]

    if context_items:
        parts.append("\n## Retrieved Context\n")
        for i, item in enumerate(context_items, 1):
            parts.append(f"[{i}] {item.snippet}")

    parts.append(_UNCERTAINTY_PROMPT.strip())

    if history:
        parts.append("\n## Conversation History")
        for msg in history[-10:]:  # last 10 messages
            role_label = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role_label}: {msg.content}")

    parts.append(f"\nUser: {user_message}")
    parts.append("Assistant:")

    return "\n".join(parts)
