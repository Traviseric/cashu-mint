"""Keyset lifecycle manager.

Handles startup initialization: ensures at least one active keyset exists
in the database, creating one from the configured master key if necessary.

Called from the FastAPI lifespan / startup handler.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from cashu_mint.config import settings
from cashu_mint.db.keyset_crud import get_active_keysets, save_keyset
from cashu_mint.nuts.keyset import generate_keyset, generate_master_key, master_key_from_hex

logger = logging.getLogger(__name__)


async def initialize_keysets(db: AsyncSession) -> None:
    """Ensure at least one active keyset exists; create one if not.

    Uses ``settings.mint_private_key`` (hex) as the master key when set.
    Falls back to a randomly generated key in development, logging a warning
    with the generated key so the operator can persist it.
    """
    active = await get_active_keysets(db)
    if active:
        logger.info(
            "Loaded %d active keyset(s): %s",
            len(active),
            [ks.id for ks in active],
        )
        return

    # No keysets — generate and persist one.
    if settings.mint_private_key:
        try:
            master_key = master_key_from_hex(settings.mint_private_key)
            logger.info("Generating keyset from MINT_PRIVATE_KEY.")
        except ValueError as exc:
            logger.error("Invalid MINT_PRIVATE_KEY: %s — generating random key.", exc)
            master_key = _random_key_with_warning()
    else:
        master_key = _random_key_with_warning()

    input_fee_ppk: int = getattr(settings, "input_fee_ppk", 0)
    unit: str = getattr(settings, "default_unit", "sat")

    keyset = generate_keyset(master_key, unit=unit, input_fee_ppk=input_fee_ppk)
    await save_keyset(db, keyset)
    logger.info("Created and persisted new keyset: %s (unit=%s)", keyset["id"], unit)


def _random_key_with_warning() -> bytes:
    key = generate_master_key()
    logger.warning(
        "MINT_PRIVATE_KEY is not set — using a random master key.  "
        "Keysets will NOT survive a restart.  "
        "To persist your keyset, set MINT_PRIVATE_KEY=%s in your .env file.",
        key.hex(),
    )
    return key
