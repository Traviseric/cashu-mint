"""NUT-01 / NUT-02 REST endpoints.

NUT-01 — GET /v1/keys
    Returns the public keys of the currently active keyset.

NUT-02 — GET /v1/keysets
    Returns the list of all keysets (id, unit, active flag, fee).

NUT-02 — GET /v1/keys/{keyset_id}
    Returns the public keys for a specific keyset.

Private keys are NEVER included in any response.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from cashu_mint.db.base import get_db
from cashu_mint.db.keyset_crud import (
    get_active_keysets,
    get_all_keysets,
    get_keyset_by_id,
    get_keyset_public_keys,
)
from cashu_mint.models.keyset_models import KeysetInfo, KeysetsResponse, KeysResponse, KeysetWithKeys

router = APIRouter(tags=["keys"])


@router.get("/keys", response_model=KeysResponse, summary="Get active keyset public keys (NUT-01)")
async def get_active_keys(db: AsyncSession = Depends(get_db)) -> KeysResponse:
    """Return the public keys of the most recently created active keyset.

    Wallets use these keys to:
    - Verify that a blinded signature was produced by this mint.
    - Know which keyset to use when requesting a blind signature.
    """
    active_keysets = await get_active_keysets(db)
    if not active_keysets:
        raise HTTPException(status_code=404, detail="No active keysets found")

    # Most recent active keyset is first (ordered newest-first in CRUD).
    keyset = active_keysets[0]
    pub_keys = await get_keyset_public_keys(db, keyset.id)

    return KeysResponse(
        keysets=[
            KeysetWithKeys(
                id=keyset.id,
                unit=keyset.unit,
                keys={str(amount): pub_hex for amount, pub_hex in pub_keys.items()},
            )
        ]
    )


@router.get(
    "/keys/{keyset_id}",
    response_model=KeysResponse,
    summary="Get public keys for a specific keyset (NUT-02)",
)
async def get_keys_for_keyset(
    keyset_id: str, db: AsyncSession = Depends(get_db)
) -> KeysResponse:
    """Return the public keys for the requested keyset ID.

    Works for both active and inactive keysets so wallets can verify old tokens.
    """
    keyset = await get_keyset_by_id(db, keyset_id)
    if keyset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Keyset '{keyset_id}' not found",
        )

    pub_keys = await get_keyset_public_keys(db, keyset_id)
    return KeysResponse(
        keysets=[
            KeysetWithKeys(
                id=keyset.id,
                unit=keyset.unit,
                keys={str(amount): pub_hex for amount, pub_hex in pub_keys.items()},
            )
        ]
    )


@router.get(
    "/keysets",
    response_model=KeysetsResponse,
    summary="List all keysets (NUT-02)",
)
async def get_keysets(db: AsyncSession = Depends(get_db)) -> KeysetsResponse:
    """Return metadata for all keysets (active and retired).

    Only id, unit, active status, and fee are returned — NOT the actual keys.
    Wallets use this to check which keysets are still redeemable.
    """
    keysets = await get_all_keysets(db)
    return KeysetsResponse(
        keysets=[
            KeysetInfo(
                id=ks.id,
                unit=ks.unit,
                active=ks.active,
                input_fee_ppk=ks.input_fee_ppk,
            )
            for ks in keysets
        ]
    )
