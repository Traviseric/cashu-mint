"""Pydantic API models for NUT-01 and NUT-02 endpoints.

These are the request/response schemas that FastAPI serializes to JSON.
No private keys are ever included.
"""

from pydantic import BaseModel


class KeysetInfo(BaseModel):
    """Keyset summary for the /v1/keysets list (NUT-02).

    Only metadata is returned — not the actual keys.
    """

    id: str
    unit: str
    active: bool
    input_fee_ppk: int = 0


class KeysetsResponse(BaseModel):
    """Response body for ``GET /v1/keysets`` (NUT-02)."""

    keysets: list[KeysetInfo]


class KeysetWithKeys(BaseModel):
    """One keyset entry in a keys-response, including denomination→pubkey map."""

    id: str
    unit: str
    keys: dict[str, str]  # denomination (as string) → compressed pubkey hex


class KeysResponse(BaseModel):
    """Response body for ``GET /v1/keys`` and ``GET /v1/keys/{keyset_id}`` (NUT-01)."""

    keysets: list[KeysetWithKeys]
