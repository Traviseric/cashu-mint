---
id: 18
title: "Implement NUT-09: Signature restore (POST /v1/restore)"
priority: P2
severity: medium
status: pending
source: feature_audit
file: "cashu_mint/nuts/restore.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Restore endpoint re-signs blinded messages — uses the same signing logic as NUT-03 swap"
---

# Implement NUT-09: Signature restore (POST /v1/restore)

**Priority:** P2 (medium)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/restore.py

## Problem

NUT-09: No signature restore endpoint. POST /v1/restore is absent. Wallets cannot recover lost tokens by replaying blinded messages.

The restore endpoint allows wallets to recover tokens after data loss (e.g., app reinstall, phone reset) by replaying their original blinded messages against the mint's signing keys. The mint re-signs any messages it previously signed, allowing the wallet to reconstruct lost tokens.

## How to Fix

Implement `cashu_mint/nuts/restore.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cashu_mint.db.database import get_db
from cashu_mint.db.models import BlindedMessageRecord  # new table needed
from cashu_mint.crypto.bdhke import step2_bob

router = APIRouter()

class RestoreRequest(BaseModel):
    outputs: list[BlindedMessage]

class RestoreResponse(BaseModel):
    outputs: list[BlindedMessage]   # echoed back
    signatures: list[BlindSignature] | None  # only for previously-signed messages
    promises: list[BlindSignature] | None    # alias for signatures

@router.post("/restore", response_model=RestoreResponse)
async def restore(req: RestoreRequest, db: Session = Depends(get_db)):
    signatures = []
    echoed_outputs = []
    for msg in req.outputs:
        # Check if this B' was previously signed (stored in db)
        existing = db.query(BlindedMessageRecord).filter(
            BlindedMessageRecord.B_ == msg.B_
        ).first()
        if existing:
            echoed_outputs.append(msg)
            signatures.append(BlindSignature(
                amount=existing.amount,
                id=existing.keyset_id,
                C_=existing.C_
            ))
    return RestoreResponse(outputs=echoed_outputs, signatures=signatures, promises=signatures)
```

Additional requirement: store all blind signatures in a `blinded_signatures` table so they can be replayed on restore.

Steps:
1. Create `blinded_signatures` database table: (B_ hex, amount, keyset_id, C_ hex)
2. In swap and mint endpoints, persist each blind signature after issuance
3. Implement `POST /v1/restore` endpoint that looks up previously-issued signatures
4. Return only the subset of requested messages that were previously signed

## Acceptance Criteria

- [ ] POST /v1/restore returns signatures for previously-signed blinded messages
- [ ] Messages never previously signed return empty response (no signatures)
- [ ] All new blind signatures stored in blinded_signatures table
- [ ] NUT-09 listed as supported in GET /v1/info

## Notes

_Generated from feature_audit finding: NUT-09 Signature Restore (medium)._
