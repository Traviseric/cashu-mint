---
id: 4
title: "Persist fee_reserve on melt quotes — add feeReserve column to PendingQuote schema"
priority: P1
severity: high
status: completed
source: gap_analyzer
file: prisma/schema.prisma
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: melt_flow
group_reason: "Same schema/repository/service files as tasks 001 and 005. Schema migration should be done together."
---

# Persist fee_reserve on melt quotes — add feeReserve column to PendingQuote schema

**Priority:** P1 (high — fee inconsistency between quote creation and retrieval)
**Source:** gap_analyzer
**Location:** prisma/schema.prisma, src/db/repository.ts, src/services/mint-service.ts

## Problem

`PendingQuote` schema has no `feeReserve` column. `createMeltQuote` in `repository.ts` accepts a `feeReserve` param but **silently drops it** — it is never stored to the database. `getMeltQuote` re-estimates fee on every call via `lightning.estimateFee()`, which could return a different value than was quoted at creation time.

This causes inconsistent API behavior:
- `POST /v1/melt/quote/bolt11` returns `fee_reserve: 100` (at quote time)
- `GET /v1/melt/quote/bolt11/{id}` may return `fee_reserve: 110` (if fee changed)

The NUT-05 spec requires `fee_reserve` to be stable for a given quote. Wallets use this value to calculate the exact input amount needed.

## How to Fix

**Step 1 — Add `feeReserve` to PendingQuote model in prisma/schema.prisma:**
```prisma
model PendingQuote {
  id          String   @id @default(cuid())
  type        String   // 'mint' | 'melt'
  bolt11      String
  amount      Int
  feeReserve  Int      @default(0)   // ← add this field
  state       String   @default("UNPAID")
  expiry      Int
  createdAt   DateTime @default(now())
}
```

**Step 2 — Run migration:**
```bash
npx prisma db push
# or: npx prisma migrate dev --name add-fee-reserve-to-pending-quote
```

**Step 3 — Update `createMeltQuote` in repository.ts to persist feeReserve:**
```typescript
async createMeltQuote(params: { id: string; bolt11: string; amount: number; feeReserve: number; expiry: number }): Promise<PendingQuote> {
  return this.prisma.pendingQuote.create({
    data: {
      id: params.id,
      type: 'melt',
      bolt11: params.bolt11,
      amount: params.amount,
      feeReserve: params.feeReserve,  // ← now persisted
      state: 'UNPAID',
      expiry: params.expiry,
    },
  });
}
```

**Step 4 — Update `getMeltQuote` in mint-service.ts to read feeReserve from DB instead of re-estimating:**
```typescript
async getMeltQuote(quoteId: string): Promise<MeltQuoteResponse> {
  const quote = await this.repo.getMeltQuote(quoteId);
  if (!quote) throw new QuoteNotFoundError(quoteId);
  // Return stored fee_reserve — no re-estimation
  return {
    quote: quoteId,
    amount: quote.amount,
    fee_reserve: quote.feeReserve,  // ← from DB, not re-estimated
    state: quote.state,
    expiry: quote.expiry,
  };
}
```

## Acceptance Criteria

- [ ] `feeReserve Int @default(0)` added to `PendingQuote` in prisma/schema.prisma
- [ ] `createMeltQuote` in repository.ts persists the feeReserve value
- [ ] `getMeltQuote` returns stored feeReserve instead of calling `lightning.estimateFee()` again
- [ ] Prisma client regenerated (`npx prisma generate`)
- [ ] Schema pushed to DB (`npx prisma db push`)
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P1, effort=low). Low-effort fix that prevents fee inconsistency between quote creation and retrieval._
