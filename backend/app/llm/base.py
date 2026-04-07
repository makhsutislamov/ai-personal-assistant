from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.models.schemas import ChatMessage


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
    ) -> ChatMessage:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
