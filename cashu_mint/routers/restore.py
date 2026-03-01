"""NUT-09: Blind signature restore endpoint.

POST /v1/restore — wallets replay their original blinded messages (B') to
recover blind signatures they previously received but lost (e.g. after
device loss or app reinstall).

The mint looks up each B' in its ``blinded_signatures`` store and returns
any signatures it previously issued.  Messages the mint never signed are
silently omitted.

This endpoint works transparently with NUT-13 deterministic secrets: because
NUT-13 secrets are derived deterministically from a BIP-32 seed, the wallet
can regenerate the exact same B' values from its seed phrase and recover
all of its lost tokens without any special mint-side support.

Reference:
    https://github.com/cashubtc/nuts/blob/main/09.md
    https://github.com/cashubtc/nuts/blob/main/13.md
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cashu_mint.db.base import get_db
from cashu_mint.db.crud import get_blind_signatures
from cashu_mint.models.base_models import BlindedMessage, BlindSignature, DLEQProof

router = APIRouter(tags=["restore"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RestoreRequest(BaseModel):
    """NUT-09 restore request body."""

    outputs: list[BlindedMessage]


class RestoreResponse(BaseModel):
    """NUT-09 restore response.

    Only the subset of requested outputs that the mint previously signed is
    echoed back.  Outputs the mint never signed are absent from both lists.
    ``outputs`` and ``signatures`` are parallel arrays of the same length.
    """

    outputs: list[BlindedMessage]
    signatures: list[BlindSignature]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/restore",
    response_model=RestoreResponse,
    summary="Restore blind signatures (NUT-09)",
)
async def restore(
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
) -> RestoreResponse:
    """Return previously-issued blind signatures for the given blinded messages.

    Wallets send their original B' values; the mint looks up any signatures
    it previously issued and returns them.  Messages not previously signed
    are silently omitted from the response.

    Combined with NUT-13 deterministic secrets, this enables full wallet
    recovery from a seed phrase without any additional mint state.
    """
    if not req.outputs:
        return RestoreResponse(outputs=[], signatures=[])

    B_values = [msg.B_ for msg in req.outputs]
    records = await get_blind_signatures(db, B_values)
    record_map = {rec.B_: rec for rec in records}

    echoed: list[BlindedMessage] = []
    sigs: list[BlindSignature] = []

    for msg in req.outputs:
        rec = record_map.get(msg.B_)
        if rec is None:
            continue
        echoed.append(msg)
        dleq = (
            DLEQProof(e=rec.dleq_e, s=rec.dleq_s)
            if rec.dleq_e and rec.dleq_s
            else None
        )
        sigs.append(
            BlindSignature(
                amount=rec.amount,
                id=rec.keyset_id,
                C_=rec.C_,
                dleq=dleq,
            )
        )

    return RestoreResponse(outputs=echoed, signatures=sigs)
