from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Any

from app.agents.base import AgentMetadata, AgentResult, BaseAgent

_FIELD_SEP = "\x1f"  # ASCII Unit Separator — safe delimiter for AppleScript field output
_RECORD_SEP = "\x1e"  # ASCII Record Separator — safe delimiter between note records
_DEFAULT_MAX_RESULTS = 10
_DEFAULT_SNIPPET_LENGTH = 500


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _sanitize(value: str) -> str:
    """Remove characters that could escape an AppleScript double-quoted string literal."""
    return value.replace("\\", "").replace('"', "").replace("\x00", "")


def _run_applescript_sync(script: str) -> tuple[str, str, int]:
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout, proc.stderr, proc.returncode


async def _run_applescript(script: str) -> tuple[str, str, int]:
    return await asyncio.to_thread(_run_applescript_sync, script)


class AppleNotesSearchAgent(BaseAgent):
    def __init__(
        self,
        max_results: int = _DEFAULT_MAX_RESULTS,
        snippet_length: int = _DEFAULT_SNIPPET_LENGTH,
    ) -> None:
        self._max_results = max_results
        self._snippet_length = snippet_length

    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="apple_notes_search",
            description=(
                "Search the user's Apple Notes for notes matching a query. "
                "Use for requests like: 'find my notes about project X', "
                "'what did I write about the meeting', "
                "'search my notes for recipe ideas', 'do I have any notes on topic Y'. "
                "Returns note titles, folders, modification dates, "
                "and a short text snippet per result. "
                "To read the full content of a specific note, "
                "use apple_notes_read with the note_id from results. "
                "Do NOT call for general questions unrelated to the user's personal Apple Notes. "
                "macOS only — returns an error on other platforms."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in note titles and content.",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, parameters: dict[str, Any]) -> AgentResult:
        if not _is_macos():
            return AgentResult(
                success=False,
                data=None,
                summary="Apple Notes search is only available on macOS.",
            )

        query = parameters.get("query", "").strip()
        if not query:
            return AgentResult(success=False, data=None, summary="No search query provided.")

        safe_query = _sanitize(query)
        script = f"""tell application "Notes"
    set fs to ASCII character 31
    set rs to ASCII character 30
    set matchingNotes to notes whose plaintext contains "{safe_query}"
    set matchingNotes to matchingNotes & (notes whose name contains "{safe_query}")
    set noteCount to count of matchingNotes
    set lim to {self._max_results}
    if noteCount < lim then set lim to noteCount
    set output to (noteCount as string) & rs
    repeat with i from 1 to lim
        set aNote to item i of matchingNotes
        set noteId to id of aNote
        set noteTitle to name of aNote
        set noteBody to plaintext of aNote
        set noteFolder to ""
        try
            set noteFolder to name of container of aNote
        end try
        set noteMod to (modification date of aNote) as string
        set output to output & noteId & fs & noteTitle & fs
        set output to output & noteBody & fs & noteFolder & fs & noteMod & rs
    end repeat
    return output
end tell"""

        stdout, stderr, returncode = await _run_applescript(script)

        if returncode != 0:
            if "not authorized" in stderr.lower() or "assistive access" in stderr.lower():
                return AgentResult(
                    success=False,
                    data=None,
                    summary="Permission denied: the app is not authorized to access Apple Notes.",
                )
            return AgentResult(
                success=False,
                data=None,
                summary=f"AppleScript error: {stderr.strip() or 'unknown error'}",
            )

        records = [r for r in stdout.split(_RECORD_SEP) if r.strip()]
        if not records:
            return AgentResult(
                success=True,
                data={"notes": [], "total_found": 0, "returned": 0, "truncated": False},
                summary=f"No notes found matching '{query}'.",
            )

        try:
            total_found = int(records[0].strip())
        except ValueError:
            total_found = 0

        notes = []
        for record in records[1:]:
            fields = record.split(_FIELD_SEP)
            if len(fields) < 5:
                continue
            note_id, title, body, folder, modified = (
                fields[0],
                fields[1],
                fields[2],
                fields[3],
                fields[4],
            )
            snippet = body[: self._snippet_length]
            notes.append(
                {
                    "note_id": note_id,
                    "title": title,
                    "folder": folder,
                    "modified": modified,
                    "snippet": snippet,
                    "snippet_truncated": len(body) > self._snippet_length,
                }
            )

        truncated = total_found > self._max_results
        return AgentResult(
            success=True,
            data={
                "notes": notes,
                "total_found": total_found,
                "returned": len(notes),
                "truncated": truncated,
            },
            summary=(
                f"Found {total_found} note(s) matching '{query}', returned {len(notes)}"
                + (" (truncated)" if truncated else "")
                + "."
            ),
        )


class AppleNotesReadAgent(BaseAgent):
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="apple_notes_read",
            description=(
                "Read the full plain-text content of a specific Apple Note by its ID. "
                "Use after apple_notes_search when you need the complete note body. "
                "The note_id must come from a previous apple_notes_search result "
                "— do NOT guess or construct IDs. "
                "macOS only — returns an error on other platforms."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": (
                            "The note ID returned by apple_notes_search "
                            "(e.g. 'x-coredata://UUID/ICNote/p123')."
                        ),
                    },
                },
                "required": ["note_id"],
            },
        )

    async def execute(self, parameters: dict[str, Any]) -> AgentResult:
        if not _is_macos():
            return AgentResult(
                success=False,
                data=None,
                summary="Apple Notes is only available on macOS.",
            )

        note_id = parameters.get("note_id", "").strip()
        if not note_id:
            return AgentResult(success=False, data=None, summary="No note_id provided.")

        safe_id = _sanitize(note_id)
        script = f"""tell application "Notes"
    set fs to ASCII character 31
    set theNote to note id "{safe_id}"
    set noteTitle to name of theNote
    set noteBody to plaintext of theNote
    set noteFolder to ""
    try
        set noteFolder to name of container of theNote
    end try
    set noteMod to (modification date of theNote) as string
    return noteTitle & fs & noteBody & fs & noteFolder & fs & noteMod
end tell"""

        stdout, stderr, returncode = await _run_applescript(script)

        if returncode != 0:
            if "not authorized" in stderr.lower() or "assistive access" in stderr.lower():
                return AgentResult(
                    success=False,
                    data=None,
                    summary="Permission denied: the app is not authorized to access Apple Notes.",
                )
            if "can't get note id" in stderr.lower() or "doesn't understand" in stderr.lower():
                return AgentResult(
                    success=False,
                    data=None,
                    summary=f"Note with ID '{note_id}' not found.",
                )
            return AgentResult(
                success=False,
                data=None,
                summary=f"AppleScript error: {stderr.strip() or 'unknown error'}",
            )

        fields = stdout.strip().split(_FIELD_SEP)
        if len(fields) < 2:
            return AgentResult(
                success=False,
                data=None,
                summary="Unexpected response from Notes.app.",
            )

        title = fields[0]
        body = fields[1]
        folder = fields[2] if len(fields) > 2 else ""
        modified = fields[3] if len(fields) > 3 else ""

        return AgentResult(
            success=True,
            data={
                "note_id": note_id,
                "title": title,
                "body": body,
                "folder": folder,
                "modified": modified,
            },
            summary=f"Retrieved note '{title}'.",
        )
