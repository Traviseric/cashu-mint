---
id: 10
title: "Implement NUT-05: Melting flow (redeem ecash for Bitcoin)"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/nuts/melt.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Melting flow uses BDHKE (task 2), database (task 3), double-spend prevention (task 6), Lightning backend (task 8)"
---

# Implement NUT-05: Melting flow (redeem ecash for Bitcoin)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/melt.py

## Problem

NUT-05: No melting flow exists. POST /v1/melt/quote/bolt11 and POST /v1/melt/bolt11 are absent. Users cannot redeem ecash for Bitcoin via Lightning.

The melting flow is the exit point for ecash: a user wants to exchange ecash tokens for Bitcoin (via Lightning payment). The flow is:
1. Wallet submits a Lightning invoice they want paid and their ecash proofs
2. Mint quotes the fee (Lightning routing fees)
3. Wallet submits proofs + quote
4. Mint verifies proofs, marks them as spent, pays the invoice, issues change

Without this flow, ecash cannot be redeemed — users would be locked in. The mint's reserves also need the melt flow to track outflows.

## How to Fix

Implement `cashu_mint/nuts/melt.py`:

```python
# POST /v1/melt/quote/bolt11
class MeltQuoteRequest(BaseModel):
    request: str    # BOLT11 invoice to pay
    unit: str = "sat"

class MeltQuoteResponse(BaseModel):
    quote: str
    amount: int         # invoice amount in sats
    fee_reserve: int    # max routing fee
    unit: str
    state: str          # UNPAID / PENDING / PAID
    expiry: int
    payment_preimage: str | None = None

@router.post("/melt/quote/bolt11", response_model=MeltQuoteResponse)
async def create_melt_quote(req: MeltQuoteRequest, db: Session = Depends(get_db)):
    # 1. Decode invoice to get amount
    invoice_amount = decode_bolt11_amount(req.request)
    # 2. Get fee estimate from Lightning backend
    fee_reserve = await lightning.get_fee_estimate(req.request)
    # 3. Store quote
    quote = MeltQuote(
        quote_id=str(uuid4()),
        request=req.request,
        unit=req.unit,
        amount=invoice_amount,
        fee_reserve=fee_reserve,
        state="UNPAID",
        expiry=int(time.time()) + 3600
    )
    db.add(quote); db.commit()
    return MeltQuoteResponse(quote=quote.quote_id, amount=invoice_amount, fee_reserve=fee_reserve, ...)

# GET /v1/melt/quote/bolt11/{quote_id}
@router.get("/melt/quote/bolt11/{quote_id}", response_model=MeltQuoteResponse)
async def get_melt_quote(quote_id: str, db: Session = Depends(get_db)):
    ...

# POST /v1/melt/bolt11
class MeltRequest(BaseModel):
    quote: str
    inputs: list[Proof]     # ecash proofs to spend
    outputs: list[BlindedMessage] | None = None  # for change (NUT-08)

@router.post("/melt/bolt11")
async def melt_tokens(req: MeltRequest, db: Session = Depends(get_db)):
    # 1. Load and validate melt quote
    quote = get_melt_quote_or_raise(db, req.quote)
    # 2. Verify input proofs (kY == C for each)
    for proof in req.inputs:
        verify_proof_or_raise(proof, db)
    # 3. Check input amounts >= invoice amount + fee_reserve
    input_total = sum(p.amount for p in req.inputs)
    required = quote.amount + quote.fee_reserve
    if input_total < required:
        raise CashuError(10000, "Insufficient inputs")
    # 4. Atomically mark proofs as spent BEFORE paying invoice
    mark_proofs_spent(db, [p.dict() for p in req.inputs])
    # 5. Pay the Lightning invoice
    result = await lightning.pay_invoice(quote.request, quote.fee_reserve)
    # 6. Update quote state
    quote.state = "PAID"
    quote.payment_preimage = result.preimage
    db.commit()
    # 7. Issue change if inputs > amount + actual_fee (NUT-08 handled separately)
    return {"paid": True, "payment_preimage": result.preimage}
```

Steps:
1. Implement `POST /v1/melt/quote/bolt11` — decode invoice, estimate fee, store quote
2. Implement `GET /v1/melt/quote/bolt11/{quote_id}` — return quote status
3. Implement `POST /v1/melt/bolt11` — verify proofs, mark spent, pay invoice
4. Mark proofs spent BEFORE paying (prevents double-claim if payment fails)
5. Handle Lightning payment failure: roll back or handle idempotently
6. Wire up BOLT11 invoice amount decoder (use `bolt11` Python library)

## Acceptance Criteria

- [ ] POST /v1/melt/quote/bolt11 returns fee estimate and quote ID
- [ ] GET /v1/melt/quote/bolt11/{id} returns current state
- [ ] POST /v1/melt/bolt11 verifies proofs, marks spent, and pays invoice
- [ ] Insufficient input amount rejected before any state changes
- [ ] Proofs marked spent atomically before Lightning payment attempt
- [ ] Quote state updated after payment: UNPAID → PENDING → PAID

## Notes

_Generated from feature_audit finding: NUT-05 Melting Tokens (critical, blocking)._
