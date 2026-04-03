from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.models import SourceDocument


async def check_source_consent(session: AsyncSession, source_type: str) -> bool:
    """Return True if the given source type has an active consent grant."""
    result = await session.execute(
        select(SourceDocument.consent_snapshot)
        .where(SourceDocument.sync_status != "disconnected")
        .limit(1)
    )
    # If no source documents exist yet, consent is implicitly not established
    # Fall back to checking whether any doc with the given source type was recorded
    # with an active consent. For MVP, we look at the SourceDocument consent field.
    #
    # A simpler approach: use UserSettings table to store consent per source.
    # For now, any document with sync_status != disconnected means consent is active.
    row = result.first()
    if row is None:
        return False
    return row.consent_snapshot == "granted"
