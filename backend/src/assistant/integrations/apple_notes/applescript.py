from __future__ import annotations

import subprocess
from datetime import timezone, UTC

from assistant.integrations.apple_notes.schemas import RawNote

# AppleScript to list folders
_FOLDERS_SCRIPT = """
tell application "Notes"
    set folderList to name of every folder
    return folderList
end tell
"""

# AppleScript to fetch notes (optionally filtered by folder)
_NOTES_SCRIPT_ALL = """
tell application "Notes"
    set noteList to {}
    repeat with n in every note
        set noteInfo to (id of n as string) & "|" & (name of n) & "|" & (body of n) & "|" & (modification date of n as string)
        set end of noteList to noteInfo
    end repeat
    return noteList
end tell
"""

_NOTES_SCRIPT_FOLDER = """
tell application "Notes"
    set noteList to {}
    set targetFolder to folder "{folder}"
    repeat with n in every note of targetFolder
        set noteInfo to (id of n as string) & "|" & (name of n) & "|" & (body of n) & "|" & (modification date of n as string)
        set end of noteList to noteInfo
    end repeat
    return noteList
end tell
"""


def _run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_folders() -> list[str]:
    output = _run_applescript(_FOLDERS_SCRIPT)
    if not output:
        return []
    return [f.strip() for f in output.split(",") if f.strip()]


def fetch_notes(folder: str | None = None) -> list[RawNote]:
    if folder:
        script = _NOTES_SCRIPT_FOLDER.format(folder=folder.replace('"', '\\"'))
    else:
        script = _NOTES_SCRIPT_ALL

    output = _run_applescript(script)
    if not output:
        return []

    notes: list[RawNote] = []
    # AppleScript returns comma-separated list items
    # Each item: id|title|body|modified_date
    for line in output.split(", "):
        parts = line.split("|", 3)
        if len(parts) < 3:
            continue
        note_id, title, body = parts[0], parts[1], parts[2]
        modified_at_str = parts[3] if len(parts) > 3 else None
        modified_at = None
        if modified_at_str:
            try:
                # macOS returns dates like: "Thursday, April 3, 2026 at 12:00:00 PM"
                # Parse as best-effort; fall back to None
                from dateutil import parser as dateutil_parser
                modified_at = dateutil_parser.parse(modified_at_str)
                if modified_at.tzinfo is None:
                    modified_at = modified_at.replace(tzinfo=UTC)
            except Exception:
                modified_at = None
        notes.append(
            RawNote(
                note_id=note_id.strip(),
                title=title.strip(),
                body=body.strip(),
                modified_at=modified_at,
                folder=folder,
            )
        )
    return notes
