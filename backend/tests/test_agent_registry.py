from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import AgentMetadata, AgentResult, BaseAgent
from app.agents.registry import AgentRegistry


class MockAgent(BaseAgent):
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="mock_agent",
            description="A mock agent for testing",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query"}
                },
                "required": ["query"],
            },
        )

    async def execute(self, parameters: dict[str, Any]) -> AgentResult:
        return AgentResult(success=True, data={"query": parameters.get("query")}, summary="Mock result")


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        agent = MockAgent()
        registry.register(agent)
        retrieved = registry.get("mock_agent")
        assert retrieved is agent

    def test_get_unregistered_returns_none(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_all_metadata(self):
        registry = AgentRegistry()
        registry.register(MockAgent())
        metadata_list = registry.all_metadata()
        assert len(metadata_list) == 1
        assert metadata_list[0].name == "mock_agent"
        assert metadata_list[0].description == "A mock agent for testing"

    def test_as_tools_returns_openai_format(self):
        registry = AgentRegistry()
        registry.register(MockAgent())
        tools = registry.as_tools()
        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert "function" in tool
        assert tool["function"]["name"] == "mock_agent"
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]
        params = tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params

    def test_register_multiple_agents(self):
        class AnotherAgent(BaseAgent):
            def metadata(self):
                return AgentMetadata(name="another", description="Another", parameters_schema={"type": "object", "properties": {}})
            async def execute(self, parameters):
                return AgentResult(success=True, data={}, summary="")

        registry = AgentRegistry()
        registry.register(MockAgent())
        registry.register(AnotherAgent())
        assert len(registry.all_metadata()) == 2
        assert len(registry.as_tools()) == 2
