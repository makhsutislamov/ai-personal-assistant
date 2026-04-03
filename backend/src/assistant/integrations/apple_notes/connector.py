from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.audit.service import log_event
from assistant.db.models import SourceDocument
from assistant.integrations.apple_notes.applescript import fetch_folders, fetch_notes
from assistant.integrations.apple_notes.schemas import ConnectionResult, RawNote, SyncResult
from assistant.memory import service as memory_service


async def connect(session: AsyncSession) -> ConnectionResult:
    """Verify AppleScript access to Apple Notes and register source."""
    try:
        folders = fetch_folders()
        doc = SourceDocument(
            source_id=str(uuid.uuid4()),
            external_ref="apple_notes://root",
            title="Apple Notes",
            sync_status="connected",
            consent_snapshot="granted",
        )
        session.add(doc)
        await session.commit()

        await log_event(
            session=session,
            action_type="integration.connect",
            target_type="source_document",
            target_id="apple_notes://root",
            before_state=None,
            after_state={"status": "connected"},
        )
        await session.commit()

        return ConnectionResult(
            connected=True,
            message="Connected to Apple Notes",
            folder_count=len(folders),
        )
    except Exception as exc:
        return ConnectionResult(connected=False, message=str(exc))


async def sync_notes(
    session: AsyncSession,
    folder_filter: list[str] | None = None,
) -> SyncResult:
    """Sync Apple Notes to memory records."""
    errors: list[str] = []
    created = updated = deleted = 0

    folders = folder_filter or [None]  # type: ignore[list-item]

    for folder in folders:
        try:
            raw_notes = fetch_notes(folder)
        except Exception as exc:
            errors.append(f"Failed to fetch folder {folder!r}: {exc}")
            continue

        for note in raw_notes:
            try:
                await _upsert_note(session, note)
                created += 1
            except Exception as exc:
                errors.append(f"Failed to sync note {note.note_id!r}: {exc}")

    return SyncResult(created=created, updated=updated, deleted=deleted, errors=errors)


async def disconnect(session: AsyncSession) -> None:
    """Revoke consent and stop syncing Apple Notes."""
    result = await session.execute(
        select(SourceDocument).where(SourceDocument.external_ref == "apple_notes://root")
    )
    docs = result.scalars().all()
    for doc in docs:
        doc.sync_status = "disconnected"
        doc.consent_snapshot = "revoked"

    await log_event(
        session=session,
        action_type="integration.disconnect",
        target_type="source_document",
        target_id="apple_notes://root",
        before_state={"status": "connected"},
        after_state={"status": "disconnected"},
    )
    await session.commit()


async def _upsert_note(session: AsyncSession, note: RawNote) -> None:
    """Create or update a memory record for a note."""
    content = f"{note.title}\n\n{note.body}".strip()
    await memory_service.auto_ingest(
        session=session,
        content=content,
        source_type="apple_notes",
        source_ref=note.note_id,
        sensitivity_class="none",
        metadata={"folder": note.folder, "modified_at": note.modified_at},
    )
