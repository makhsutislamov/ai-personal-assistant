import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AzureOpenAISettings,
    ChatMessage,
    OllamaSettings,
    SettingsSchema,
    TokenEvent,
    ToolCall,
    UserMessagePayload,
)


class TestSettingsSchema:
    def test_default_values(self):
        settings = SettingsSchema()
        assert settings.llm_provider == "ollama"
        assert settings.ollama.base_url == "http://localhost:11434"
        assert settings.ollama.model == "llama3.1"

    def test_round_trip_json(self):
        settings = SettingsSchema(
            llm_provider="azure_openai",
            ollama=OllamaSettings(base_url="http://custom:11434", model="llama3.2"),
            azure_openai=AzureOpenAISettings(
                endpoint="https://myaccount.openai.azure.com/",
                api_key="secret",
                deployment="gpt-4o",
                api_version="2024-03-01",
            ),
        )
        json_str = settings.model_dump_json()
        loaded = SettingsSchema.model_validate_json(json_str)
        assert loaded == settings

    def test_invalid_provider(self):
        with pytest.raises(ValidationError):
            SettingsSchema(llm_provider="invalid_provider")  # type: ignore


class TestUserMessagePayload:
    def test_valid_payload(self):
        payload = UserMessagePayload(session_id="abc-123", content="Hello")
        assert payload.session_id == "abc-123"
        assert payload.content == "Hello"
        assert payload.type == "message"

    def test_missing_session_id(self):
        with pytest.raises(ValidationError):
            UserMessagePayload(content="Hello")  # type: ignore

    def test_missing_content(self):
        with pytest.raises(ValidationError):
            UserMessagePayload(session_id="abc-123")  # type: ignore


class TestChatMessage:
    def test_simple_user_message(self):
        msg = ChatMessage(role="user", content="Hi there")
        assert msg.role == "user"
        assert msg.content == "Hi there"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_assistant_with_tool_calls(self):
        tool_call = ToolCall(
            id="call_001",
            function={"name": "file_search", "arguments": '{"pattern": "*.py"}'},
        )
        msg = ChatMessage(role="assistant", content=None, tool_calls=[tool_call])
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_001"

    def test_tool_result_message(self):
        msg = ChatMessage(role="tool", content="Found 3 files", tool_call_id="call_001")
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_001"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="test")  # type: ignore


class TestStreamEvents:
    def test_token_event(self):
        event = TokenEvent(content="Hello")
        assert event.type == "token"
        assert event.content == "Hello"
