from __future__ import annotations

import asyncio
import fnmatch
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentMetadata, AgentResult, BaseAgent

_DEFAULT_MAX_RESULTS = 100

# macOS volume duplicates to skip
_MACOS_SKIP_DIRS = frozenset(
    [
        "/System/Volumes/Data",
        "/System/Volumes/Preboot",
        "/System/Volumes/Recovery",
        "/System/Volumes/VM",
    ]
)


@dataclass
class FileResult:
    name: str
    path: str
    last_modified: float
    size_bytes: int


@dataclass
class SearchResult:
    files: list[FileResult] = field(default_factory=list)
    directories_searched: int = 0
    directories_skipped: int = 0
    skipped_reasons: list[str] = field(default_factory=list)
    truncated: bool = False


def _is_glob_pattern(pattern: str) -> bool:
    return any(c in pattern for c in ("*", "?", "["))


def _matches(filename: str, pattern: str) -> bool:
    if _is_glob_pattern(pattern):
        return fnmatch.fnmatch(filename.lower(), pattern.lower())
    return pattern.lower() in filename.lower()


def _search_sync(pattern: str, directory: str, max_results: int) -> SearchResult:
    result = SearchResult()
    queue = [directory]

    while queue:
        if len(result.files) >= max_results:
            result.truncated = True
            break

        current_dir = queue.pop(0)

        # Skip macOS volume duplicates
        if sys.platform == "darwin" and current_dir in _MACOS_SKIP_DIRS:
            result.directories_skipped += 1
            result.skipped_reasons.append(f"macOS volume duplicate: {current_dir}")
            continue

        try:
            with os.scandir(current_dir) as entries:
                result.directories_searched += 1
                for entry in entries:
                    if len(result.files) >= max_results:
                        result.truncated = True
                        break
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            queue.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            if _matches(entry.name, pattern):
                                stat = entry.stat(follow_symlinks=False)
                                result.files.append(
                                    FileResult(
                                        name=entry.name,
                                        path=entry.path,
                                        last_modified=stat.st_mtime,
                                        size_bytes=stat.st_size,
                                    )
                                )
                    except (PermissionError, OSError):
                        pass
        except PermissionError as exc:
            result.directories_skipped += 1
            result.skipped_reasons.append(f"Permission denied: {current_dir}")
        except OSError as exc:
            result.directories_skipped += 1
            result.skipped_reasons.append(f"OS error in {current_dir}: {exc}")

    return result


class FileSearchAgent(BaseAgent):
    def __init__(self, max_results: int = _DEFAULT_MAX_RESULTS) -> None:
        self._max_results = max_results

    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="file_search",
            description=(
                "Search the local filesystem for files matching a name or glob pattern. "
                "Only call this tool when the user explicitly asks to find, search for, or "
                "locate files on their computer. "
                "Do NOT call this tool for greetings, general questions, or any message "
                "that does not clearly request a file search."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": (
                            "File name pattern to search for. Supports glob wildcards "
                            "(e.g. '*.py', 'report*.pdf') or plain text substring match."
                        ),
                    },
                    "directory": {
                        "type": "string",
                        "description": (
                            "Root directory to search from. Defaults to the user home directory '~'. "
                            "Use '/' to search the entire filesystem."
                        ),
                    },
                },
                "required": ["pattern"],
            },
        )

    async def execute(self, parameters: dict[str, Any]) -> AgentResult:
        pattern = parameters.get("pattern", "")
        directory = parameters.get("directory") or os.path.expanduser("~")
        directory = os.path.expanduser(directory)

        if not pattern:
            return AgentResult(success=False, data=None, summary="No search pattern provided.")

        search_result = await asyncio.to_thread(
            _search_sync, pattern, directory, self._max_results
        )

        files_data = [
            {
                "name": f.name,
                "path": f.path,
                "last_modified": f.last_modified,
                "size_bytes": f.size_bytes,
            }
            for f in search_result.files
        ]

        summary = (
            f"Found {len(files_data)} file(s) matching '{pattern}'"
            + (f" (results truncated to {self._max_results})" if search_result.truncated else "")
            + f". Searched {search_result.directories_searched} director(ies), "
            f"skipped {search_result.directories_skipped}."
        )

        return AgentResult(
            success=True,
            data={
                "files": files_data,
                "directories_searched": search_result.directories_searched,
                "directories_skipped": search_result.directories_skipped,
                "skipped_reasons": search_result.skipped_reasons,
                "truncated": search_result.truncated,
            },
            summary=summary,
        )
