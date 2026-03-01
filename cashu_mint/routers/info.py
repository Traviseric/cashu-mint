"""NUT-06: Mint information endpoint.

GET /v1/info — returns mint metadata, contact info, and supported NUT list.

Reference: https://github.com/cashubtc/nuts/blob/main/06.md
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from cashu_mint.config import settings

router = APIRouter(tags=["info"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class NutSupportEntry(BaseModel):
    """One entry in the ``nuts`` map — describes a supported NUT."""

    disabled: bool = False


class MintInfoContact(BaseModel):
    method: str
    info: str


class MintInfoResponse(BaseModel):
    """Response for ``GET /v1/info`` (NUT-06)."""

    name: str
    pubkey: str = ""
    version: str
    description: str
    description_long: str = ""
    contact: list[MintInfoContact] = Field(default_factory=list)
    motd: str = ""
    nuts: dict[str, NutSupportEntry]


# ---------------------------------------------------------------------------
# Supported NUTs
# ---------------------------------------------------------------------------

# Map of NUT number (as string) → support descriptor.
# Add new NUT entries here as they are implemented.
_SUPPORTED_NUTS: dict[str, dict] = {
    "1": {"disabled": False},   # Mint public keys
    "2": {"disabled": False},   # Keysets and fees
    "9": {"disabled": False},   # Signature restore (NUT-09)
    "10": {"disabled": False},  # Well-known spending conditions (NUT-10)
    "11": {"disabled": False},  # Pay-to-Pubkey / P2PK (NUT-11)
    "12": {"disabled": False},  # DLEQ proofs (NUT-12)
    "13": {"disabled": False},  # Deterministic secrets (NUT-13, wallet-side)
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/info",
    response_model=MintInfoResponse,
    summary="Mint information (NUT-06)",
)
async def get_mint_info() -> MintInfoResponse:
    """Return metadata and capability flags for this mint.

    Wallets use this endpoint to discover:
    - Mint name, description, contact details
    - Which NUTs (protocol features) are supported
    """
    return MintInfoResponse(
        name=settings.mint_name,
        version="Cashu-Mint/0.1.0",
        description=settings.mint_description,
        description_long=settings.mint_description_long,
        motd=settings.mint_motd,
        nuts={nut: NutSupportEntry(**entry) for nut, entry in _SUPPORTED_NUTS.items()},
    )
