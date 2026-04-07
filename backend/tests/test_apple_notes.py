from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agents.apple_notes import (
    _FIELD_SEP,
    _RECORD_SEP,
    AppleNotesReadAgent,
    AppleNotesSearchAgent,
    _sanitize,
)


def _make_proc(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


def _build_search_output(total_found: int, notes: list[dict]) -> str:
    """Build the mock AppleScript output for a search call."""
    records = [str(total_found)]
    for n in notes:
        record = _FIELD_SEP.join([n["note_id"], n["title"], n["body"], n["folder"], n["modified"]])
        records.append(record)
    return _RECORD_SEP.join(records) + _RECORD_SEP


def _build_read_output(
    title: str, body: str, folder: str = "Notes", modified: str = "Sunday, April 6, 2026"
) -> str:
    return _FIELD_SEP.join([title, body, folder, modified])


class TestAppleNotesSearchAgent:
    @pytest.fixture
    def agent(self):
        return AppleNotesSearchAgent(max_results=10, snippet_length=500)

    @pytest.mark.asyncio
    async def test_search_success_returns_notes(self, agent):
        notes = [
            {
                "note_id": "x-coredata://uuid/ICNote/p1",
                "title": "Meeting Notes",
                "body": "Discussed Q2 goals.",
                "folder": "Work",
                "modified": "Monday, April 1, 2026",
            },
        ]
        proc = _make_proc(stdout=_build_search_output(1, notes))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "meeting"})

        assert result.success is True
        assert len(result.data["notes"]) == 1
        assert result.data["notes"][0]["title"] == "Meeting Notes"
        assert result.data["notes"][0]["note_id"] == "x-coredata://uuid/ICNote/p1"
        assert result.data["notes"][0]["folder"] == "Work"
        assert result.data["total_found"] == 1
        assert result.data["returned"] == 1
        assert result.data["truncated"] is False

    @pytest.mark.asyncio
    async def test_search_snippet_truncated(self, agent):
        long_body = "A" * 600
        notes = [
            {
                "note_id": "x-coredata://uuid/ICNote/p2",
                "title": "Long Note",
                "body": long_body,
                "folder": "Notes",
                "modified": "Monday, April 1, 2026",
            },
        ]
        proc = _make_proc(stdout=_build_search_output(1, notes))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "long"})

        assert result.success is True
        note = result.data["notes"][0]
        assert len(note["snippet"]) == 500
        assert note["snippet_truncated"] is True

    @pytest.mark.asyncio
    async def test_search_snippet_not_truncated_when_short(self, agent):
        short_body = "Short body."
        notes = [
            {
                "note_id": "x-coredata://uuid/ICNote/p3",
                "title": "Short Note",
                "body": short_body,
                "folder": "Notes",
                "modified": "Monday, April 1, 2026",
            },
        ]
        proc = _make_proc(stdout=_build_search_output(1, notes))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "short"})

        note = result.data["notes"][0]
        assert note["snippet"] == short_body
        assert note["snippet_truncated"] is False

    @pytest.mark.asyncio
    async def test_search_max_results_cap(self):
        agent = AppleNotesSearchAgent(max_results=3, snippet_length=500)
        notes = [
            {
                "note_id": f"x-coredata://uuid/ICNote/p{i}",
                "title": f"Note {i}",
                "body": "content",
                "folder": "Notes",
                "modified": "Monday, April 1, 2026",
            }
            for i in range(3)
        ]
        # total_found = 10 but only 3 returned (script already capped via AppleScript)
        proc = _make_proc(stdout=_build_search_output(10, notes))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "note"})

        assert result.success is True
        assert len(result.data["notes"]) == 3
        assert result.data["total_found"] == 10
        assert result.data["truncated"] is True

    @pytest.mark.asyncio
    async def test_search_zero_results(self, agent):
        proc = _make_proc(stdout=_build_search_output(0, []))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "xyznonexistent"})

        assert result.success is True
        assert result.data["notes"] == []
        assert result.data["total_found"] == 0
        assert result.data["truncated"] is False

    @pytest.mark.asyncio
    async def test_search_non_macos_returns_failure(self, agent):
        with patch("app.agents.apple_notes._is_macos", return_value=False):
            result = await agent.execute({"query": "meeting"})

        assert result.success is False
        assert "macOS" in result.summary

    @pytest.mark.asyncio
    async def test_search_permission_denied(self, agent):
        proc = _make_proc(
            returncode=1, stderr="Notes got an error: not authorized to send Apple events"
        )

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "meeting"})

        assert result.success is False
        assert "permission" in result.summary.lower() or "not authorized" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_search_applescript_error(self, agent):
        proc = _make_proc(returncode=1, stderr="syntax error")

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"query": "meeting"})

        assert result.success is False
        assert "syntax error" in result.summary

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_failure(self, agent):
        result = await agent.execute({"query": ""})
        assert result.success is False

    def test_search_metadata_schema(self, agent):
        meta = agent.metadata()
        assert meta.name == "apple_notes_search"
        assert isinstance(meta.description, str)
        assert "apple_notes_read" in meta.description
        schema = meta.parameters_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_search_metadata_aci_guidance(self, agent):
        meta = agent.metadata()
        assert "do not" in meta.description.lower()
        assert "macOS" in meta.description


class TestAppleNotesReadAgent:
    @pytest.fixture
    def agent(self):
        return AppleNotesReadAgent()

    @pytest.mark.asyncio
    async def test_read_success(self, agent):
        note_id = "x-coredata://uuid/ICNote/p42"
        body = "This is the full note content.\nWith multiple lines."
        proc = _make_proc(stdout=_build_read_output("Project Plan", body, "Work"))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"note_id": note_id})

        assert result.success is True
        assert result.data["title"] == "Project Plan"
        assert result.data["body"] == body
        assert result.data["folder"] == "Work"
        assert result.data["note_id"] == note_id

    @pytest.mark.asyncio
    async def test_read_note_not_found(self, agent):
        proc = _make_proc(
            returncode=1, stderr='Notes got an error: Can\'t get note id "x-coredata://bad".'
        )

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"note_id": "x-coredata://bad"})

        assert result.success is False
        assert "not found" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_read_non_macos_returns_failure(self, agent):
        with patch("app.agents.apple_notes._is_macos", return_value=False):
            result = await agent.execute({"note_id": "x-coredata://uuid/ICNote/p1"})

        assert result.success is False
        assert "macOS" in result.summary

    @pytest.mark.asyncio
    async def test_read_permission_denied(self, agent):
        proc = _make_proc(returncode=1, stderr="not authorized to send Apple events to Notes")

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"note_id": "x-coredata://uuid/ICNote/p1"})

        assert result.success is False
        assert "permission" in result.summary.lower() or "not authorized" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_read_empty_note_id_returns_failure(self, agent):
        result = await agent.execute({"note_id": ""})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_read_result_has_expected_fields(self, agent):
        proc = _make_proc(stdout=_build_read_output("My Note", "Some content", "Personal"))

        with patch(
            "app.agents.apple_notes._run_applescript_sync",
            return_value=(proc.stdout, proc.stderr, proc.returncode),
        ):
            result = await agent.execute({"note_id": "x-coredata://uuid/ICNote/p99"})

        assert result.success is True
        for field in ("note_id", "title", "body", "folder", "modified"):
            assert field in result.data

    def test_read_metadata_schema(self, agent):
        meta = agent.metadata()
        assert meta.name == "apple_notes_read"
        assert isinstance(meta.description, str)
        schema = meta.parameters_schema
        assert schema["type"] == "object"
        assert "note_id" in schema["properties"]
        assert "note_id" in schema["required"]

    def test_read_metadata_aci_guidance(self, agent):
        meta = agent.metadata()
        assert "do not" in meta.description.lower()
        assert "apple_notes_search" in meta.description


class TestSanitize:
    def test_removes_double_quotes(self):
        assert '"' not in _sanitize('hello "world"')

    def test_removes_backslashes(self):
        assert "\\" not in _sanitize("path\\to\\file")

    def test_removes_null_bytes(self):
        assert "\x00" not in _sanitize("hello\x00world")

    def test_preserves_normal_text(self):
        assert _sanitize("meeting notes Q2") == "meeting notes Q2"

    def test_preserves_single_quotes(self):
        assert "'" in _sanitize("it's a note")
