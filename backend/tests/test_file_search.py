from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.file_search import FileSearchAgent


class TestFileSearchAgent:
    @pytest.fixture
    def agent(self):
        return FileSearchAgent(max_results=100)

    @pytest.mark.asyncio
    async def test_search_existing_files(self, tmp_path, agent):
        (tmp_path / "hello.txt").write_text("content")
        (tmp_path / "world.txt").write_text("content")
        (tmp_path / "notes.md").write_text("content")

        result = await agent.execute({"pattern": "*.txt", "directory": str(tmp_path)})

        assert result.success is True
        file_names = {f["name"] for f in result.data["files"]}
        assert "hello.txt" in file_names
        assert "world.txt" in file_names
        assert "notes.md" not in file_names

    @pytest.mark.asyncio
    async def test_search_no_results(self, tmp_path, agent):
        (tmp_path / "hello.txt").write_text("content")

        result = await agent.execute({"pattern": "*.xyz", "directory": str(tmp_path)})

        assert result.success is True
        assert result.data["files"] == []

    @pytest.mark.asyncio
    async def test_search_plain_text_substring(self, tmp_path, agent):
        (tmp_path / "report_2024.pdf").write_text("content")
        (tmp_path / "invoice.pdf").write_text("content")

        result = await agent.execute({"pattern": "report", "directory": str(tmp_path)})

        assert result.success is True
        names = [f["name"] for f in result.data["files"]]
        assert "report_2024.pdf" in names
        assert "invoice.pdf" not in names

    @pytest.mark.asyncio
    async def test_search_permission_error(self, tmp_path, agent):
        (tmp_path / "accessible.txt").write_text("content")

        def scandir_side_effect(path):
            if str(path) == str(tmp_path):
                raise PermissionError("No access")
            raise PermissionError("No access")

        with patch("os.scandir", side_effect=scandir_side_effect):
            result = await agent.execute({"pattern": "*.txt", "directory": str(tmp_path)})

        assert result.success is True
        assert result.data["directories_skipped"] >= 1

    @pytest.mark.asyncio
    async def test_result_limit(self, tmp_path):
        agent = FileSearchAgent(max_results=10)
        for i in range(50):
            (tmp_path / f"file_{i:03d}.txt").write_text("content")

        result = await agent.execute({"pattern": "*.txt", "directory": str(tmp_path)})

        assert result.success is True
        assert len(result.data["files"]) <= 10
        assert result.data["truncated"] is True

    @pytest.mark.asyncio
    async def test_result_limit_100_default(self, tmp_path, agent):
        for i in range(150):
            (tmp_path / f"file_{i:03d}.txt").write_text("content")

        result = await agent.execute({"pattern": "*.txt", "directory": str(tmp_path)})

        assert result.success is True
        assert len(result.data["files"]) <= 100

    @pytest.mark.asyncio
    async def test_metadata_schema(self, agent):
        meta = agent.metadata()
        assert meta.name == "file_search"
        assert isinstance(meta.description, str)
        assert len(meta.description) > 0
        schema = meta.parameters_schema
        assert schema["type"] == "object"
        assert "pattern" in schema["properties"]
        assert "pattern" in schema["required"]

    @pytest.mark.asyncio
    async def test_empty_pattern_returns_failure(self, tmp_path, agent):
        result = await agent.execute({"pattern": "", "directory": str(tmp_path)})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_file_result_has_expected_fields(self, tmp_path, agent):
        test_file = tmp_path / "sample.txt"
        test_file.write_text("hello")

        result = await agent.execute({"pattern": "sample.txt", "directory": str(tmp_path)})

        assert result.success is True
        assert len(result.data["files"]) == 1
        file_entry = result.data["files"][0]
        assert "name" in file_entry
        assert "path" in file_entry
        assert "last_modified" in file_entry
        assert "size_bytes" in file_entry

    @pytest.mark.asyncio
    async def test_nested_directory_search(self, tmp_path, agent):
        nested = tmp_path / "subdir" / "deep"
        nested.mkdir(parents=True)
        (nested / "deep_file.txt").write_text("content")

        result = await agent.execute({"pattern": "deep_file.txt", "directory": str(tmp_path)})

        assert result.success is True
        assert any(f["name"] == "deep_file.txt" for f in result.data["files"])

    def test_metadata_description_contains_aci_guidance(self, agent):
        from app.agents.registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(agent)
        tools = registry.as_tools()

        desc = tools[0]["function"]["description"]
        assert "find my resume" in desc
        assert "do not" in desc.lower()
        assert "last-modified timestamp" in desc
