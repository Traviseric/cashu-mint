"""Repository functions for all database models.

All functions are async and expect a SQLAlchemy ``AsyncSession``.
Proof insertion uses a SELECT + INSERT pattern under SERIALIZABLE isolation
to ensure atomic double-spend prevention.
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cashu_mint.db.keyset_models import Keyset, KeysetKey
from cashu_mint.db.models import MeltQuote, MintQuote, Proof


# ---------------------------------------------------------------------------
# Keyset CRUD
# ---------------------------------------------------------------------------


async def get_active_keysets(db: AsyncSession) -> Sequence[Keyset]:
    result = await db.execute(select(Keyset).where(Keyset.active == True))  # noqa: E712
    return result.scalars().all()


async def get_keyset_by_id(db: AsyncSession, keyset_id: str) -> Optional[Keyset]:
    result = await db.execute(select(Keyset).where(Keyset.id == keyset_id))
    return result.scalar_one_or_none()


async def get_all_keysets(db: AsyncSession) -> Sequence[Keyset]:
    result = await db.execute(select(Keyset))
    return result.scalars().all()


async def create_keyset(db: AsyncSession, keyset: Keyset) -> Keyset:
    db.add(keyset)
    await db.flush()
    return keyset


async def deactivate_keyset(db: AsyncSession, keyset_id: str) -> None:
    await db.execute(
        update(Keyset).where(Keyset.id == keyset_id).values(active=False)
    )
    await db.flush()


async def get_keyset_keys(db: AsyncSession, keyset_id: str) -> Sequence[KeysetKey]:
    result = await db.execute(
        select(KeysetKey).where(KeysetKey.keyset_id == keyset_id)
    )
    return result.scalars().all()


async def create_keyset_key(db: AsyncSession, key: KeysetKey) -> KeysetKey:
    db.add(key)
    await db.flush()
    return key


# ---------------------------------------------------------------------------
# Proof CRUD (double-spend prevention)
# ---------------------------------------------------------------------------


async def get_proof(db: AsyncSession, Y: str) -> Optional[Proof]:
    """Return a proof by its Y value, or None if not found."""
    result = await db.execute(select(Proof).where(Proof.Y == Y))
    return result.scalar_one_or_none()


async def get_proofs(db: AsyncSession, Y_values: list[str]) -> Sequence[Proof]:
    """Return all proofs matching the given Y values."""
    result = await db.execute(select(Proof).where(Proof.Y.in_(Y_values)))
    return result.scalars().all()


async def spend_proof(db: AsyncSession, proof: Proof) -> Proof:
    """Atomically insert a spent-proof record.

    Raises:
        IntegrityError: if this Y value is already in the database
            (i.e., the token was already spent).  Callers MUST catch this
            and translate it to a CashuError(10001).
    """
    db.add(proof)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise
    return proof


async def spend_proofs(db: AsyncSession, proofs: list[Proof]) -> None:
    """Atomically insert multiple spent-proof records.

    All proofs are flushed in a single round-trip so the operation is
    effectively atomic within the session.

    Raises:
        IntegrityError: if any Y value is already spent.
    """
    for p in proofs:
        db.add(p)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise


async def count_spent_proofs(db: AsyncSession) -> int:
    from sqlalchemy import func
    result = await db.execute(select(func.count()).select_from(Proof))
    return result.scalar_one()


# ---------------------------------------------------------------------------
# MintQuote CRUD
# ---------------------------------------------------------------------------


async def create_mint_quote(db: AsyncSession, quote: MintQuote) -> MintQuote:
    db.add(quote)
    await db.flush()
    return quote


async def get_mint_quote(db: AsyncSession, quote_id: str) -> Optional[MintQuote]:
    result = await db.execute(select(MintQuote).where(MintQuote.quote_id == quote_id))
    return result.scalar_one_or_none()


async def update_mint_quote_state(
    db: AsyncSession, quote_id: str, state: str
) -> None:
    await db.execute(
        update(MintQuote).where(MintQuote.quote_id == quote_id).values(state=state)
    )
    await db.flush()


async def count_mint_quotes_by_state(db: AsyncSession, state: str) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count())
        .select_from(MintQuote)
        .where(MintQuote.state == state)
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# MeltQuote CRUD
# ---------------------------------------------------------------------------


async def create_melt_quote(db: AsyncSession, quote: MeltQuote) -> MeltQuote:
    db.add(quote)
    await db.flush()
    return quote


async def get_melt_quote(db: AsyncSession, quote_id: str) -> Optional[MeltQuote]:
    result = await db.execute(select(MeltQuote).where(MeltQuote.quote_id == quote_id))
    return result.scalar_one_or_none()


async def update_melt_quote(
    db: AsyncSession,
    quote_id: str,
    *,
    state: Optional[str] = None,
    payment_preimage: Optional[str] = None,
    change: Optional[str] = None,
) -> None:
    values: dict = {}
    if state is not None:
        values["state"] = state
    if payment_preimage is not None:
        values["payment_preimage"] = payment_preimage
    if change is not None:
        values["change"] = change
    if values:
        await db.execute(
            update(MeltQuote).where(MeltQuote.quote_id == quote_id).values(**values)
        )
        await db.flush()


async def count_melt_quotes_by_state(db: AsyncSession, state: str) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count())
        .select_from(MeltQuote)
        .where(MeltQuote.state == state)
    )
    return result.scalar_one()
