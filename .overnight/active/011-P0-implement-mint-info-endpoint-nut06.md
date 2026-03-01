---
id: 11
title: "Implement NUT-06: Mint info endpoint (GET /v1/info)"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/nuts/info.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: parallel
context_group: protocol_extensions
group_reason: "Info endpoint is mostly independent of other NUTs — it's a read-only static response"
---

# Implement NUT-06: Mint info endpoint (GET /v1/info)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/info.py

## Problem

NUT-06: No mint info endpoint exists. GET /v1/info is absent. Wallets cannot discover the mint's capabilities, supported NUTs, or contact info.

The info endpoint is the discovery mechanism for the Cashu ecosystem. Wallets call it to:
- Determine which NUTs the mint supports
- Find the mint's public key (for identification)
- Discover accepted payment methods
- Get mint name, description, and contact details

Without this endpoint, wallets cannot interoperate with the mint (many wallets check /v1/info first to feature-detect).

## How to Fix

Implement `cashu_mint/nuts/info.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ContactInfo(BaseModel):
    method: str     # "email", "twitter", "nostr", etc.
    info: str       # contact details

class NutSupport(BaseModel):
    disabled: bool = False

class MintInfoResponse(BaseModel):
    name: str
    pubkey: str         # mint's public identity key (hex)
    version: str        # "Cashu-Mint/0.1.0"
    description: str
    description_long: str | None = None
    contact: list[ContactInfo] = []
    motd: str | None = None   # message of the day
    icon_url: str | None = None
    nuts: dict[str, dict]     # NUT number -> support info

@router.get("/info", response_model=MintInfoResponse)
async def get_mint_info():
    return MintInfoResponse(
        name=settings.MINT_NAME,
        pubkey=get_mint_pubkey(),   # Derive from MINT_PRIVATE_KEY
        version="Cashu-Mint/0.1.0",
        description=settings.MINT_DESCRIPTION,
        contact=[],
        nuts={
            "4": {
                "methods": [{"method": "bolt11", "unit": "sat"}],
                "disabled": False
            },
            "5": {
                "methods": [{"method": "bolt11", "unit": "sat"}],
                "disabled": False
            },
            "7": {"supported": True},
            "9": {"supported": False},
            "10": {"supported": False},
            "11": {"supported": False},
            "12": {"supported": False},
        }
    )
```

Steps:
1. Implement `GET /v1/info` with `MintInfoResponse` Pydantic model
2. Read mint name, description from configuration (`settings.py`)
3. Derive mint public key from `MINT_PRIVATE_KEY` env var
4. Declare supported NUTs accurately (only what is implemented)
5. Include payment methods for NUT-04 and NUT-05 (bolt11/sat)
6. Update NUT support map as features are added

## Acceptance Criteria

- [ ] GET /v1/info returns valid JSON per NUT-06 spec
- [ ] Response includes mint name, pubkey, version, description
- [ ] `nuts` field accurately reflects implemented NUTs
- [ ] Payment methods listed for NUT-04 and NUT-05
- [ ] Mint name and description configurable via environment variables

## Notes

_Generated from feature_audit finding: NUT-06 Mint Info (critical, blocking)._
