---
id: 6
title: "Fix getMeltQuote to check expiry like getMintQuote does"
priority: P1
severity: medium
status: completed
source: gap_analyzer
file: src/services/mint-service.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: melt_flow
group_reason: "Same mint-service.ts melt flow as tasks 001, 005. Low-effort fix in same file."
---

# Fix getMeltQuote to check expiry like getMintQuote does

**Priority:** P1 (medium — inconsistent quote expiry behavior)
**Source:** gap_analyzer
**Location:** src/services/mint-service.ts

## Problem

`getMintQuote` correctly checks quote expiry and transitions the quote to `EXPIRED` state:
```typescript
// getMintQuote does this:
if (quote.state === 'UNPAID' && Date.now() > quote.expiry * 1000) {
  await this.repo.updateMintQuoteState(quoteId, 'EXPIRED');
  return { ...quote, state: 'EXPIRED' };
}
```

But `getMeltQuote` does **not** check expiry — it always returns the current DB state even if the quote expired hours ago. This is inconsistent behavior that could allow wallets to attempt melts on expired quotes, wasting fees or causing confusing errors.

## How to Fix

Add the same expiry check to `getMeltQuote` in `mint-service.ts`:

```typescript
async getMeltQuote(quoteId: string): Promise<MeltQuoteResponse> {
  const quote = await this.repo.getMeltQuote(quoteId);
  if (!quote) throw new QuoteNotFoundError(quoteId);

  // Check expiry — mirror getMintQuote behavior
  if (quote.state === 'UNPAID' && Date.now() > quote.expiry * 1000) {
    await this.repo.updateMeltQuoteState(quoteId, 'EXPIRED');
    return {
      quote: quoteId,
      amount: quote.amount,
      fee_reserve: quote.feeReserve,
      state: 'EXPIRED',
      expiry: quote.expiry,
    };
  }

  return {
    quote: quoteId,
    amount: quote.amount,
    fee_reserve: quote.feeReserve,
    state: quote.state,
    expiry: quote.expiry,
  };
}
```

Also add `updateMeltQuoteState(quoteId, state)` to `repository.ts` if it doesn't already exist (check — `updateMintQuoteState` exists, a parallel method for melt quotes may be needed or it may be the same generic method).

## Acceptance Criteria

- [ ] `getMeltQuote` checks `quote.expiry` and transitions to `EXPIRED` if past expiry
- [ ] `updateMeltQuoteState` (or equivalent) exists in repository.ts
- [ ] Behavior mirrors `getMintQuote` expiry handling
- [ ] Unit test: `getMeltQuote` returns EXPIRED state for past-expiry UNPAID quote
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P1, effort=low). Simple consistency fix — mirrors existing getMintQuote behavior._
