---
id: 14
title: "Implement NUT-07: Token state check (POST /v1/checkstate)"
priority: P1
severity: high
status: pending
source: feature_audit
file: "cashu_mint/nuts/checkstate.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Token state check queries the same spent proofs store as double-spend prevention (task 6)"
---

# Implement NUT-07: Token state check (POST /v1/checkstate)

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/checkstate.py

## Problem

NUT-07: No token state check endpoint. POST /v1/checkstate is absent. Wallets cannot verify if their tokens are still spendable without this endpoint.

Wallets need to check if tokens are spent before attempting to use them (e.g., after recovering from backup, after network failure during a send). Without this endpoint, wallets have no way to detect stale tokens except by trying to spend them and receiving an error.

## How to Fix

Implement `cashu_mint/nuts/checkstate.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cashu_mint.db.database import get_db
from cashu_mint.db.crud import compute_Y
from cashu_mint.db.models import Proof

router = APIRouter()

class CheckStateRequest(BaseModel):
    Ys: list[str]   # list of Y-coordinate hex strings (proof identifiers)

class ProofState(BaseModel):
    Y: str
    state: str      # UNSPENT / SPENT / PENDING

class CheckStateResponse(BaseModel):
    states: list[ProofState]

@router.post("/checkstate", response_model=CheckStateResponse)
async def check_state(req: CheckStateRequest, db: Session = Depends(get_db)):
    states = []
    for Y in req.Ys:
        proof = db.query(Proof).filter(Proof.Y == Y).first()
        state = "SPENT" if proof else "UNSPENT"
        states.append(ProofState(Y=Y, state=state))
    return CheckStateResponse(states=states)
```

Note: PENDING state is used when a proof is locked in a pending melt operation. For simplicity, start with UNSPENT/SPENT only, then add PENDING tracking as a follow-up.

Steps:
1. Implement `POST /v1/checkstate` endpoint
2. Accept list of Y values (compressed pubkey hex, 66 chars each)
3. Query proofs table for each Y value
4. Return SPENT if found in proofs table, UNSPENT if not
5. Add to NUT-07 entry in GET /v1/info supported nuts list

## Acceptance Criteria

- [ ] POST /v1/checkstate returns state for each submitted Y value
- [ ] Spent tokens return state="SPENT"
- [ ] Unspent tokens return state="UNSPENT"
- [ ] Batch requests supported (list of Y values)
- [ ] NUT-07 listed as supported in GET /v1/info response

## Notes

_Generated from feature_audit finding: NUT-07 Token State Check (high)._
