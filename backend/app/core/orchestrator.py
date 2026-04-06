from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from app.agents.registry import AgentRegistry
from app.core.session import SessionStore
from app.llm.base import BaseLLMProvider
from app.models.schemas import (
    AgentResultEvent,
    AgentStatusEvent,
    ChatMessage,
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    TokenEvent,
)

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 5

_SYSTEM_PROMPT = """You are a helpful personal AI assistant running on the user's desktop.
You have access to a set of tools that can interact with the user's system and retrieve information on their behalf.

## Tool use
- Before selecting a tool, reason briefly about which tool best matches the user's request.
- You may call multiple tools in sequence if the task requires it (e.g., search for a file, then read its contents).
- Each tool's description specifies exactly when to use it — follow those boundaries strictly.
- If a tool returns an error or empty results, explain what happened and suggest what the user could try instead.
- Never invoke a tool speculatively or to satisfy curiosity — only when the user's request clearly requires it.

## Responses
- After using tools, synthesize the results into a clear, direct answer — don't just dump raw data.
- Use markdown formatting (tables, bullet lists, code blocks) where it aids readability.
- For conversational messages, general questions, or anything not requiring system access, respond directly without invoking any tools."""


class Orchestrator:
    def __init__(
        self,
        provider: BaseLLMProvider,
        registry: AgentRegistry,
        session_store: SessionStore,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._session_store = session_store

    async def handle_message(
        self, session_id: str, content: str
    ) -> AsyncIterator[StreamEvent]:
        return self._handle_message_gen(session_id, content)

    async def _handle_message_gen(
        self, session_id: str, content: str
    ) -> AsyncIterator[StreamEvent]:
        # Append user message
        user_msg = ChatMessage(role="user", content=content)
        self._session_store.append_message(session_id, user_msg)

        # Build message list: system prompt + conversation history
        history = self._session_store.get_history(session_id)
        messages = [ChatMessage(role="system", content=_SYSTEM_PROMPT)] + history
        tools = self._registry.as_tools()

        try:
            # First LLM call (non-streaming) to detect tool use
            response_msg = await self._provider.chat_completion(messages, tools=tools or None)

            if response_msg.tool_calls:
                # Tool calling path
                async for event in self._handle_tool_calls(
                    session_id, response_msg, messages
                ):
                    yield event
            else:
                # Direct text streaming path
                async for event in self._stream_direct(session_id, messages, response_msg):
                    yield event

        except Exception as exc:
            logger.exception("Error in orchestrator handle_message")
            yield ErrorEvent(code="orchestrator_error", message=str(exc))

        yield DoneEvent()

    async def _handle_tool_calls(
        self,
        session_id: str,
        response_msg: ChatMessage,
        messages: list[ChatMessage],
    ) -> AsyncIterator[StreamEvent]:
        # Multi-turn tool loop: re-call LLM after each round of tool results
        # until it produces a plain response or _MAX_TOOL_ITERATIONS is reached.
        tools = self._registry.as_tools()
        iteration = 0

        while response_msg.tool_calls and iteration < _MAX_TOOL_ITERATIONS:
            iteration += 1
            messages = messages + [response_msg]

            for tool_call in response_msg.tool_calls or []:
                tool_name = tool_call.function.get("name", "")
                agent = self._registry.get(tool_name)

                yield AgentStatusEvent(agent_name=tool_name, status="working")

                if agent is None:
                    tool_result_msg = ChatMessage(
                        role="tool",
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tool_call.id,
                    )
                    messages = messages + [tool_result_msg]
                    yield AgentStatusEvent(agent_name=tool_name, status="error")
                    continue

                try:
                    args_raw = tool_call.function.get("arguments", "{}")
                    parameters = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})

                    agent_result = await agent.execute(parameters)

                    yield AgentStatusEvent(agent_name=tool_name, status="complete")
                    yield AgentResultEvent(agent_name=tool_name, data=agent_result.data)

                    tool_result_msg = ChatMessage(
                        role="tool",
                        content=json.dumps(agent_result.data) if agent_result.data else agent_result.summary,
                        tool_call_id=tool_call.id,
                    )
                    messages = messages + [tool_result_msg]

                except Exception as exc:
                    logger.exception("Error executing agent %s", tool_name)
                    tool_result_msg = ChatMessage(
                        role="tool",
                        content=f"Error executing {tool_name}: {exc}",
                        tool_call_id=tool_call.id,
                    )
                    messages = messages + [tool_result_msg]
                    yield AgentStatusEvent(agent_name=tool_name, status="error")

            # Re-call LLM — it decides whether to invoke more tools or produce final answer
            response_msg = await self._provider.chat_completion(messages, tools=tools or None)

        if iteration >= _MAX_TOOL_ITERATIONS:
            logger.warning(
                "Max tool iterations (%d) reached for session %s", _MAX_TOOL_ITERATIONS, session_id
            )

        # Synthesis — delegate to _stream_direct; if response_msg already has content
        # (LLM chose to answer without further tool calls) it yields that directly.
        async for event in self._stream_direct(session_id, messages, response_msg):
            yield event

    async def _stream_direct(
        self,
        session_id: str,
        messages: list[ChatMessage],
        first_response: ChatMessage,
    ) -> AsyncIterator[StreamEvent]:
        # If the non-streaming detection call already returned text, yield it directly
        # to avoid a redundant second LLM round-trip.
        # Otherwise re-issue a streaming call to get the response.
        full_content = ""

        if first_response.content:
            full_content = first_response.content
            yield TokenEvent(content=first_response.content)
        else:
            stream = await self._provider.chat_completion_stream(messages)
            async for token in stream:
                full_content += token
                yield TokenEvent(content=token)

        if full_content:
            assistant_msg = ChatMessage(role="assistant", content=full_content)
            self._session_store.append_message(session_id, assistant_msg)
