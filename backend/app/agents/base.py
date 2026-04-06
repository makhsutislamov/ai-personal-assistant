from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMetadata:
    name: str
    description: str
    parameters_schema: dict[str, Any]


@dataclass
class AgentResult:
    success: bool
    data: Any
    summary: str


class BaseAgent(ABC):
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        ...

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> AgentResult:
        ...
