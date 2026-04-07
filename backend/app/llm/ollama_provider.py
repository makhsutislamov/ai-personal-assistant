from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import ollama

from app.llm.base import BaseLLMProvider
from app.models.schemas import ChatMessage, OllamaSettings, ToolCall

logger = logging.getLogger(__name__)


def _to_ollama_messages(messages: list[ChatMessage]) -> list[dict]:
    result = []
    for msg in messages:
        item: dict = {"role": msg.role}
        if msg.content is not None:
            item["content"] = msg.content
        if msg.tool_calls:
            item["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.get("name", ""),
                        "arguments": (
                            tc.function["arguments"]
                            if isinstance(tc.function.get("arguments"), dict)
                            else json.loads(tc.function.get("arguments") or "{}")
                        ),
                    },
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id is not None:
            item["tool_call_id"] = msg.tool_call_id
        result.append(item)
    return result


def _parse_message(msg: ollama.Message) -> ChatMessage:
    tool_calls = None
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        tool_calls = [
            ToolCall(
                id=getattr(tc, "id", f"call_{i}"),
                function={
                    "name": tc.function.name if hasattr(tc, "function") else "",
                    "arguments": (
                        tc.function.arguments
                        if hasattr(tc, "function") and tc.function.arguments
                        else {}
                    ),
                },
            )
            for i, tc in enumerate(msg.tool_calls)
        ]
    return ChatMessage(
        role=msg.role,  # type: ignore[arg-type]
        content=msg.content or None,
        tool_calls=tool_calls,
    )


class OllamaProvider(BaseLLMProvider):
    def __init__(self, settings: OllamaSettings) -> None:
        self._settings = settings
        self._client = ollama.AsyncClient(host=settings.base_url)

    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": self._settings.model,
            "messages": _to_ollama_messages(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        async def _gen():
            async for part in await self._client.chat(**kwargs):
                content = part.message.content
                if content:
                    yield content

        return _gen()

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> ChatMessage:
        kwargs: dict = {
            "model": self._settings.model,
            "messages": _to_ollama_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.chat(**kwargs)
        return _parse_message(response.message)

    async def health_check(self) -> bool:
        try:
            await self._client.list()
            return True
        except Exception:
            return False
