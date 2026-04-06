from __future__ import annotations

import json

from app.agents.base import AgentMetadata, BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        meta = agent.metadata()
        self._agents[meta.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def all_metadata(self) -> list[AgentMetadata]:
        return [agent.metadata() for agent in self._agents.values()]

    def as_tools(self) -> list[dict]:
        tools = []
        for meta in self.all_metadata():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": meta.name,
                        "description": meta.description,
                        "parameters": meta.parameters_schema,
                    },
                }
            )
        return tools
