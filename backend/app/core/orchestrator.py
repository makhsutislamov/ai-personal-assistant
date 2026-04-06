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

_SYSTEM_PROMPT = """You are a helpful personal AI assistant running on the user's desktop.

You have access to tools that can interact with the user's system.
IMPORTANT: Only call a tool when the user's message explicitly asks you to search for or find files on their computer.
Never call a tool for greetings, general questions, or any message that is not a clear file-search request.
For casual conversation, questions, or anything unrelated to file searching, respond directly using your knowledge — do NOT invoke any tools.

When you do use a tool, explain what you are doing and summarize the results clearly.
Format file lists as markdown tables or bullet lists for readability."""


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
        # Add the assistant's tool-call message to history
        messages = messages + [response_msg]

        for tool_call in response_msg.tool_calls or []:
            tool_name = tool_call.function.get("name", "")
            agent = self._registry.get(tool_name)

            yield AgentStatusEvent(agent_name=tool_name, status="working")

            if agent is None:
                error_content = f"Unknown tool: {tool_name}"
                tool_result_msg = ChatMessage(
                    role="tool",
                    content=error_content,
                    tool_call_id=tool_call.id,
                )
                messages = messages + [tool_result_msg]
                yield AgentStatusEvent(agent_name=tool_name, status="error")
                continue

            try:
                # Parse arguments
                args_raw = tool_call.function.get("arguments", "{}")
                if isinstance(args_raw, str):
                    parameters = json.loads(args_raw)
                else:
                    parameters = args_raw or {}

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

        # Synthesis call — stream the final response
        full_content = ""
        try:
            stream = await self._provider.chat_completion_stream(messages)
            async for token in stream:
                full_content += token
                yield TokenEvent(content=token)
        except Exception as exc:
            logger.exception("Error streaming synthesis response")
            yield ErrorEvent(code="stream_error", message=str(exc))

        if full_content:
            assistant_msg = ChatMessage(role="assistant", content=full_content)
            self._session_store.append_message(session_id, assistant_msg)

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
