---
id: 7
title: "Implement NUT-03: Token swap (POST /v1/swap)"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/nuts/swap.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Token swap is the core wallet operation — uses BDHKE engine (task 2), database (task 3), and double-spend prevention (task 6)"
---

# Implement NUT-03: Token swap (POST /v1/swap)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/swap.py

## Problem

NUT-03: No token swap endpoint exists. POST /v1/swap (split/merge tokens) is the core everyday wallet operation and is completely missing.

The swap endpoint is the most frequently used endpoint in the Cashu protocol. Wallets use it to:
- Split large tokens into smaller denominations (change)
- Merge tokens from different keysets
- Send tokens to another wallet (sender creates locked tokens)
- Receive tokens (recipient verifies and re-issues)

Without this endpoint, wallets cannot manage their token denomination distribution and cannot perform basic send/receive flows.

## How to Fix

Implement `cashu_mint/nuts/swap.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from cashu_mint.db.database import get_db
from cashu_mint.db.crud import mark_proofs_spent, get_keyset_key
from cashu_mint.crypto.bdhke import verify, step2_bob

router = APIRouter()

class BlindedMessage(BaseModel):
    amount: int
    id: str        # keyset ID
    B_: str        # blinded message hex

class Proof(BaseModel):
    amount: int
    id: str        # keyset ID
    secret: str
    C: str         # unblinded signature hex

class SwapRequest(BaseModel):
    inputs: list[Proof]
    outputs: list[BlindedMessage]

class BlindSignature(BaseModel):
    amount: int
    id: str
    C_: str        # blind signature hex

class SwapResponse(BaseModel):
    signatures: list[BlindSignature]

@router.post("/swap", response_model=SwapResponse)
async def swap(request: SwapRequest, db: Session = Depends(get_db)):
    # 1. Validate input amounts == output amounts
    input_total = sum(p.amount for p in request.inputs)
    output_total = sum(m.amount for m in request.outputs)
    if input_total != output_total:
        raise ValueError("Input and output amounts do not match")

    # 2. Verify each input proof (kY == C)
    for proof in request.inputs:
        private_key = get_keyset_key(db, proof.id, proof.amount)
        if not verify(proof.secret, bytes.fromhex(proof.C), private_key):
            raise ValueError("Invalid proof")

    # 3. Atomically mark inputs as spent (raises DoubleSpendError if reused)
    mark_proofs_spent(db, [p.dict() for p in request.inputs])

    # 4. Blind-sign outputs
    signatures = []
    for msg in request.outputs:
        private_key = get_keyset_key(db, msg.id, msg.amount)
        C_prime = step2_bob(bytes.fromhex(msg.B_), private_key)
        signatures.append(BlindSignature(
            amount=msg.amount,
            id=msg.id,
            C_=C_prime.hex()
        ))

    db.commit()
    return SwapResponse(signatures=signatures)
```

Steps:
1. Implement Pydantic models: `SwapRequest`, `SwapResponse`, `Proof`, `BlindedMessage`, `BlindSignature`
2. Implement proof validation using BDHKE `verify()`
3. Implement atomic proof marking (call `mark_proofs_spent()` from task 6)
4. Implement blind signing loop using BDHKE `step2_bob()`
5. Validate input total == output total (no inflation)
6. Handle fee deduction if `input_fee_ppk > 0` (per NUT-02)
7. Register router on POST /v1/swap

## Acceptance Criteria

- [ ] POST /v1/swap with valid proofs returns blind signatures
- [ ] Invalid proofs rejected with error code 10002
- [ ] Already-spent proofs rejected with error code 10001
- [ ] Input amount != output amount rejected (prevents inflation)
- [ ] All operations wrapped in single database transaction
- [ ] Works with multiple input/output denominations

## Notes

_Generated from feature_audit finding: NUT-03 Token Swap (critical, blocking)._
