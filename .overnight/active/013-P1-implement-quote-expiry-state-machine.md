---
id: 13
title: "Implement quote expiry and state machine (UNPAID/PAID/ISSUED/EXPIRED)"
priority: P1
severity: high
status: pending
source: feature_audit
file: "cashu_mint/db/crud.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: token_lifecycle
group_reason: "Quote expiry builds on database layer (task 3) and affects mint/melt endpoints (tasks 9, 10)"
---

# Implement quote expiry and state machine (UNPAID/PAID/ISSUED/EXPIRED)

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/db/crud.py

## Problem

No quote expiry management. Mint and melt quotes must expire after a configurable TTL. No quote state machine or cleanup job exists.

Without quote expiry:
- Expired Lightning invoices stay in UNPAID state forever
- Wallets might try to use expired quotes
- Database grows unboundedly with stale quotes
- The mint might attempt to pay expired invoices

## How to Fix

1. Implement quote state transitions in CRUD:
```python
# Quote state machine:
# MintQuote:  UNPAID → PAID → ISSUED
#                ↓
#             EXPIRED (if TTL elapsed without payment)
#
# MeltQuote: UNPAID → PENDING → PAID
#               ↓
#            EXPIRED (if TTL elapsed)

def expire_stale_quotes(db: Session) -> int:
    """Mark all quotes past their expiry time as EXPIRED. Returns count."""
    now = int(time.time())
    count = db.query(MintQuote).filter(
        MintQuote.state == "UNPAID",
        MintQuote.expiry < now
    ).update({"state": "EXPIRED"})
    db.query(MeltQuote).filter(
        MeltQuote.state == "UNPAID",
        MeltQuote.expiry < now
    ).update({"state": "EXPIRED"})
    db.commit()
    return count

def check_quote_expiry(quote) -> None:
    """Raise error if quote is expired."""
    if quote.state == "EXPIRED":
        raise CashuError(11004, "Quote has expired")
    if int(time.time()) > quote.expiry:
        quote.state = "EXPIRED"
        raise CashuError(11004, "Quote has expired")
```

2. Add background cleanup task:
```python
# cashu_mint/tasks.py
import asyncio

async def quote_cleanup_task(db_factory, interval_seconds: int = 300):
    """Background task: expire stale quotes every 5 minutes."""
    while True:
        async with db_factory() as db:
            count = expire_stale_quotes(db)
            if count:
                logger.info(f"Expired {count} stale quotes")
        await asyncio.sleep(interval_seconds)
```

3. Start background task in app lifespan:
```python
@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(quote_cleanup_task(get_db))
    yield
```

Steps:
1. Add `expire_stale_quotes()` to CRUD layer
2. Add expiry check to all quote-consuming endpoints (mint, melt)
3. Create background `quote_cleanup_task` that runs periodically
4. Start cleanup task in FastAPI lifespan
5. Add `MINT_QUOTE_TTL` and `MELT_QUOTE_TTL` to configuration

## Acceptance Criteria

- [ ] Expired quotes cannot be used (returns error code 11004)
- [ ] Background task marks UNPAID quotes as EXPIRED after TTL
- [ ] Background task runs without blocking request handling
- [ ] Quote TTL is configurable via environment variable
- [ ] GET quote endpoints return EXPIRED state accurately

## Notes

_Generated from feature_audit finding: Quote Expiry & State Machine (medium)._
