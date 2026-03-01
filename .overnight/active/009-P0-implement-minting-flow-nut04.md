---
id: 9
title: "Implement NUT-04: Minting flow (deposit Bitcoin, receive ecash)"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/nuts/mint.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Minting flow uses BDHKE (task 2), database (task 3), Lightning backend (task 8), and keyset management (task 5)"
---

# Implement NUT-04: Minting flow (deposit Bitcoin, receive ecash)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/mint.py

## Problem

NUT-04: No minting flow exists. POST /v1/mint/quote/bolt11 and POST /v1/mint/bolt11 are absent. Users cannot deposit Bitcoin and receive ecash.

The minting flow is the entry point for ecash: a user wants to exchange Bitcoin (via Lightning) for ecash tokens. The flow is:
1. Wallet requests a Lightning invoice from the mint (quote)
2. User pays the invoice
3. Wallet submits blinded messages to the mint
4. Mint verifies payment and issues blind signatures

Without this flow, the mint cannot onboard new users or receive any Bitcoin reserves.

## How to Fix

Implement two endpoints in `cashu_mint/nuts/mint.py`:

```python
# POST /v1/mint/quote/bolt11
class MintQuoteRequest(BaseModel):
    amount: int
    unit: str = "sat"

class MintQuoteResponse(BaseModel):
    quote: str           # UUID quote ID
    request: str         # BOLT11 invoice
    unit: str
    state: str           # UNPAID / PAID / ISSUED
    expiry: int          # Unix timestamp

@router.post("/mint/quote/bolt11", response_model=MintQuoteResponse)
async def create_mint_quote(req: MintQuoteRequest, db: Session = Depends(get_db)):
    # 1. Validate amount within mint limits
    # 2. Create Lightning invoice via backend
    invoice = await lightning.create_invoice(req.amount, memo="Cashu mint")
    # 3. Store quote in database
    quote = MintQuote(
        quote_id=str(uuid4()),
        request=invoice.payment_request,
        unit=req.unit,
        amount=req.amount,
        state="UNPAID",
        expiry=int(time.time()) + 3600  # 1 hour
    )
    db.add(quote); db.commit()
    return MintQuoteResponse(
        quote=quote.quote_id,
        request=invoice.payment_request,
        unit=req.unit,
        state="UNPAID",
        expiry=quote.expiry
    )

# GET /v1/mint/quote/bolt11/{quote_id}
@router.get("/mint/quote/bolt11/{quote_id}", response_model=MintQuoteResponse)
async def get_mint_quote(quote_id: str, db: Session = Depends(get_db)):
    quote = db.query(MintQuote).filter(MintQuote.quote_id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    # Check if invoice was paid
    if quote.state == "UNPAID":
        paid = await lightning.check_invoice(extract_payment_hash(quote.request))
        if paid:
            quote.state = "PAID"
            db.commit()
    return MintQuoteResponse(...)

# POST /v1/mint/bolt11
class MintRequest(BaseModel):
    quote: str
    outputs: list[BlindedMessage]

@router.post("/mint/bolt11", response_model=MintResponse)
async def mint_tokens(req: MintRequest, db: Session = Depends(get_db)):
    # 1. Load and validate quote
    quote = get_quote_or_raise(db, req.quote)
    if quote.state != "PAID":
        raise CashuError(11002, "Quote not paid")
    if quote.state == "ISSUED":
        raise CashuError(11003, "Quote already used")
    # 2. Validate output amounts sum == quote amount
    # 3. Blind-sign all outputs
    signatures = [sign_blinded_message(msg, db) for msg in req.outputs]
    # 4. Mark quote as ISSUED
    quote.state = "ISSUED"
    db.commit()
    return MintResponse(signatures=signatures)
```

Steps:
1. Implement `POST /v1/mint/quote/bolt11` — create Lightning invoice, store quote
2. Implement `GET /v1/mint/quote/bolt11/{quote_id}` — poll for payment status
3. Implement `POST /v1/mint/bolt11` — issue tokens for paid quote
4. Validate: quote must be PAID, amount must match, quote can only be used once
5. Handle concurrent requests (two wallets both try to claim same quote)

## Acceptance Criteria

- [ ] POST /v1/mint/quote/bolt11 creates a Lightning invoice and quote record
- [ ] GET /v1/mint/quote/bolt11/{id} checks Lightning payment status and updates quote state
- [ ] POST /v1/mint/bolt11 issues blind signatures when quote is PAID
- [ ] Quote state transitions: UNPAID → PAID → ISSUED (no going back)
- [ ] Attempting to re-use an ISSUED quote returns error
- [ ] Output amounts must sum to quote amount exactly

## Notes

_Generated from feature_audit finding: NUT-04 Minting Tokens (critical, blocking)._
