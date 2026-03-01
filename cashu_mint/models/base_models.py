"""Shared Pydantic models used across multiple NUT endpoints.

Includes the core BlindedMessage / BlindSignature / Proof types that appear
in NUT-03 (swap), NUT-04 (mint), and NUT-05 (melt) request/response bodies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# NUT-12: DLEQ proof
# ---------------------------------------------------------------------------


class DLEQProof(BaseModel):
    """Discrete Log Equality proof included in BlindSignature responses.

    Allows wallets to cryptographically verify that the mint signed with the
    key it advertised (NUT-12 offline verification).

    Both fields are 64-character lowercase hex strings (32 bytes each).
    """

    e: str = Field(..., description="Fiat–Shamir challenge (32-byte hex)")
    s: str = Field(..., description="Schnorr response scalar (32-byte hex)")


# ---------------------------------------------------------------------------
# NUT-00 / NUT-03 / NUT-04 / NUT-05: core token types
# ---------------------------------------------------------------------------


class BlindedMessage(BaseModel):
    """A wallet's blinded token request — sent to the mint for signing.

    ``B_`` is the 33-byte compressed secp256k1 point B' = Y + r·G,
    serialised as a lowercase hex string (66 chars).
    """

    amount: int = Field(..., gt=0, description="Token denomination in base unit")
    id: str = Field(..., description="Keyset ID the wallet is requesting a signature from")
    B_: str = Field(..., description="Blinded message point B' (33-byte compressed, hex)")


class BlindSignature(BaseModel):
    """Mint's response to a BlindedMessage — the blind signature C'.

    ``C_`` is the 33-byte compressed secp256k1 point C' = k·B',
    serialised as a lowercase hex string (66 chars).

    ``dleq`` is included when NUT-12 is supported, allowing offline
    verification of the mint's signature.
    """

    amount: int = Field(..., description="Token denomination in base unit")
    id: str = Field(..., description="Keyset ID that produced this signature")
    C_: str = Field(..., description="Blinded signature point C' (33-byte compressed, hex)")
    dleq: DLEQProof | None = Field(
        default=None,
        description="Optional DLEQ proof for offline verification (NUT-12)",
    )


class Proof(BaseModel):
    """An unblinded token proof held by a wallet.

    Presented to the mint when spending (swap / melt).
    """

    amount: int = Field(..., description="Token denomination in base unit")
    id: str = Field(..., description="Keyset ID")
    secret: str = Field(..., description="Token secret")
    C: str = Field(..., description="Unblinded signature C (33-byte compressed, hex)")
    witness: str | None = Field(
        default=None,
        description="Optional spending-condition witness (NUT-10/11)",
    )
