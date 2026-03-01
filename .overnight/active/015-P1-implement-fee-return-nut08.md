---
id: 15
title: "Implement NUT-08: Overpaid Lightning fee return (change tokens)"
priority: P1
severity: high
status: pending
source: feature_audit
file: "cashu_mint/nuts/melt.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "NUT-08 is an extension of the NUT-05 melt flow — modifies the melt endpoint to issue change"
---

# Implement NUT-08: Overpaid Lightning fee return (change tokens)

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/melt.py

## Problem

NUT-08: No overpaid Lightning fee handling. When a Lightning payment costs less than quoted, the user should receive change tokens. This is missing.

When a wallet melts tokens, it provides `fee_reserve` to cover routing fees. The actual routing fee is often less than the reserve. Without NUT-08, the difference is lost — the mint keeps it. This means users are routinely overcharged for withdrawals.

Example: quoted fee_reserve = 10 sats, actual fee = 3 sats → user is owed 7 sats change.

## How to Fix

Extend the melt endpoint to accept optional `outputs` for change:

```python
# Extend MeltRequest model
class MeltRequest(BaseModel):
    quote: str
    inputs: list[Proof]
    outputs: list[BlindedMessage] | None = None  # optional change outputs

# In POST /v1/melt/bolt11 handler, after payment:
async def melt_tokens(req: MeltRequest, db: Session = Depends(get_db)):
    # ... (existing melt logic) ...

    # After paying invoice, calculate change
    actual_fee = result.fee_sat
    change_amount = quote.fee_reserve - actual_fee

    signatures = []
    if req.outputs and change_amount > 0:
        # Issue change tokens for the fee difference
        outputs_total = sum(o.amount for o in req.outputs)
        if outputs_total != change_amount:
            # Outputs must sum to exactly the change amount
            raise CashuError(10000, f"Change outputs must sum to {change_amount} sats")

        for msg in req.outputs:
            private_key = get_keyset_key(db, msg.id, msg.amount)
            C_prime = step2_bob(bytes.fromhex(msg.B_), private_key)
            signatures.append(BlindSignature(
                amount=msg.amount,
                id=msg.id,
                C_=C_prime.hex()
            ))

    db.commit()
    return {
        "paid": True,
        "payment_preimage": result.preimage,
        "change": [sig.dict() for sig in signatures]
    }
```

Steps:
1. Add `outputs` optional field to `MeltRequest` model
2. After Lightning payment, calculate `actual_fee` from payment result
3. If `outputs` provided and `change_amount > 0`, blind-sign change outputs
4. Validate outputs sum == change_amount
5. Include change signatures in melt response
6. Update GET /v1/info to advertise NUT-08 support

## Acceptance Criteria

- [ ] `outputs` field accepted in POST /v1/melt/bolt11 request
- [ ] Change tokens issued when actual fee < quoted fee_reserve
- [ ] Change outputs must sum to exactly (fee_reserve - actual_fee)
- [ ] No change issued if outputs not provided (user forfeits excess fee)
- [ ] NUT-08 listed as supported in GET /v1/info

## Notes

_Generated from feature_audit finding: NUT-08 Overpaid Lightning Fees (high)._
