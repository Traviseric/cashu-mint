---
id: 6
title: "Implement double-spend prevention with atomic proof tracking"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/db/crud.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Double-spend prevention is a shared mechanism used by NUT-03 swap, NUT-04 mint, and NUT-05 melt — all token operations call this"
---

# Implement double-spend prevention with atomic proof tracking

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/db/crud.py

## Problem

No double-spend prevention exists. The mint must track all spent proofs (by their Y-coordinate or secret hash) and reject reuse. Without this, the entire ecash system is exploitable.

An attacker can submit the same ecash proof in concurrent requests to the swap or melt endpoint and receive double the value. This is a critical security vulnerability — the mint would be losing funds.

The fix requires atomic check-and-mark semantics: checking if a proof is spent AND marking it as spent must happen in a single indivisible database operation. A simple sequential read-then-write is vulnerable to TOCTOU race conditions under concurrent load.

## How to Fix

Implement atomic proof insertion with unique constraint enforcement:

```python
# cashu_mint/db/crud.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from cashu_mint.db.models import Proof
from cashu_mint.crypto.bdhke import hash_to_curve

class DoubleSpendError(Exception):
    code = 10001  # Token already spent (NUT error code)

def compute_Y(secret: str) -> str:
    """Compute Y = hash_to_curve(secret) as hex — the proof identifier."""
    Y_point = hash_to_curve(secret.encode())
    return Y_point.format(compressed=True).hex()

def mark_proofs_spent(db: Session, proofs: list[dict]) -> None:
    """
    Atomically mark multiple proofs as spent.
    Raises DoubleSpendError if any proof was already spent.
    Uses database UNIQUE constraint on Y to prevent races.
    """
    db_proofs = []
    for proof in proofs:
        Y = compute_Y(proof["secret"])
        db_proofs.append(Proof(
            Y=Y,
            amount=proof["amount"],
            keyset_id=proof["id"],
            secret=proof["secret"],
            C=proof["C"]
        ))
    try:
        db.add_all(db_proofs)
        db.flush()  # Let DB enforce UNIQUE constraint immediately
    except IntegrityError:
        db.rollback()
        raise DoubleSpendError("Token is already spent")

def is_proof_spent(db: Session, secret: str) -> bool:
    """Check if a single proof has been spent."""
    Y = compute_Y(secret)
    return db.query(Proof).filter(Proof.Y == Y).first() is not None
```

Database constraint (in migration):
```sql
ALTER TABLE proofs ADD CONSTRAINT proofs_Y_unique UNIQUE (Y);
```

Steps:
1. Add UNIQUE constraint on `proofs.Y` in Alembic migration
2. Implement `compute_Y()` using `hash_to_curve` from BDHKE engine
3. Implement `mark_proofs_spent()` with atomic batch insert
4. Implement `is_proof_spent()` for single-proof checks
5. Wrap all token operations (swap, mint, melt) in database transactions
6. All proof batch operations must use a single transaction (all-or-nothing)

## Acceptance Criteria

- [ ] UNIQUE constraint on `proofs.Y` enforced at database level
- [ ] Concurrent duplicate submissions: exactly one succeeds, rest get `DoubleSpendError`
- [ ] Batch proof marking is atomic: all succeed or all fail (no partial spends)
- [ ] NUT error code 10001 returned to wallet on double-spend attempt
- [ ] Test: submit same proof twice concurrently — second request fails cleanly

## Notes

_Generated from feature_audit finding: Double-Spend Prevention (critical, blocking)._
