from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import openai

from app.llm.base import BaseLLMProvider
from app.models.schemas import AzureOpenAISettings, ChatMessage, ToolCall

logger = logging.getLogger(__name__)


def _to_openai_messages(messages: list[ChatMessage]) -> list[dict]:
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
                    "function": tc.function,
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id is not None:
            item["tool_call_id"] = msg.tool_call_id
        result.append(item)
    return result


def _parse_choice_message(msg) -> ChatMessage:
    tool_calls = None
    if msg.tool_calls:
        tool_calls = [
            ToolCall(
                id=tc.id,
                function={"name": tc.function.name, "arguments": tc.function.arguments},
            )
            for tc in msg.tool_calls
        ]
    return ChatMessage(
        role=msg.role,  # type: ignore[arg-type]
        content=msg.content,
        tool_calls=tool_calls,
    )


class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, settings: AzureOpenAISettings) -> None:
        self._settings = settings
        self._client = openai.AsyncAzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
        )

    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": self._settings.deployment,
            "messages": _to_openai_messages(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        async def _gen():
            async with await self._client.chat.completions.create(**kwargs) as stream:
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        return _gen()

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> ChatMessage:
        kwargs: dict = {
            "model": self._settings.deployment,
            "messages": _to_openai_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.chat.completions.create(**kwargs)
        return _parse_choice_message(response.choices[0].message)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
