from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from assistant.integrations.apple_notes.applescript import fetch_folders, fetch_notes


def test_fetch_folders_parses_list():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Personal, Work, Travel")
        folders = fetch_folders()
    assert folders == ["Personal", "Work", "Travel"]


def test_fetch_folders_empty_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        folders = fetch_folders()
    assert folders == []


def test_fetch_folders_applescript_error():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Notes not accessible", stdout="")
        with pytest.raises(RuntimeError, match="AppleScript error"):
            fetch_folders()


def test_fetch_notes_parses_output():
    raw_output = "note-1|Meeting|Discussion notes|Thursday, April 3, 2026 at 12:00:00 PM"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=raw_output)
        notes = fetch_notes()

    assert len(notes) == 1
    assert notes[0].note_id == "note-1"
    assert notes[0].title == "Meeting"
    assert notes[0].body == "Discussion notes"


def test_fetch_notes_empty_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        notes = fetch_notes()
    assert notes == []
