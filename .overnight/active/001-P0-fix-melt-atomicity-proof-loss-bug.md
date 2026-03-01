---
id: 1
title: "Fix melt atomicity bug — prevent permanent proof loss on Lightning payment failure"
priority: P0
severity: critical
status: completed
source: gap_analyzer + feature_audit
file: src/services/mint-service.ts
line: 456
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: melt_flow
group_reason: "Same melt flow as tasks 005, 006. Also touches repository.ts and prisma/schema.prisma alongside task 004."
---

# Fix melt atomicity bug — prevent permanent proof loss on Lightning payment failure

**Priority:** P0 (critical — fund loss bug)
**Source:** gap_analyzer + feature_audit
**Location:** src/services/mint-service.ts:456-461

## Problem

The NUT-05 melt flow has a critical fund-loss bug: proofs are atomically spent (written to SpentProof table) before the Lightning payment is attempted. If `sendPayment()` fails after `spendProofsAndSignAtomically` succeeds, the user's proofs are permanently burned with zero compensation.

The current code comment at line 457 acknowledges this explicitly:
```
// Payment failed — ideally should unspend proofs, but for Phase 1
// we mark the quote as UNPAID (proofs are already spent though)
```

This breaks the atomicity guarantee for melt. A wallet submitting a valid melt request could lose their tokens permanently due to a transient Lightning failure, network timeout, or routing error.

**Current broken flow:**
1. `spendProofsAndSignAtomically()` — marks proofs SPENT in DB ✓
2. `sendPayment()` — Lightning call — can fail ✗
3. On failure: quote set to UNPAID, proofs remain SPENT (lost forever)

## How to Fix

Implement a two-phase commit for melt using a PENDING proof state:

**Phase 1 — Lock proofs as PENDING (not yet spent):**
1. Add a `PendingProof` model to `prisma/schema.prisma` (or add a `state` field to an existing model: `PENDING | SPENT`). Fields: `Y` (point), `amount`, `keysetId`, `meltQuoteId`, `createdAt`.
2. In `repository.ts`, add `lockProofsAsPending(proofs, quoteId)` — inserts into PendingProof table (or marks existing entries as PENDING). Use a SERIALIZABLE transaction to prevent double-spend against both SpentProof and PendingProof.
3. Add `burnPendingProofs(quoteId)` — moves PendingProofs for this quoteId into SpentProof (or marks them SPENT).
4. Add `releasePendingProofs(quoteId)` — deletes PendingProofs for this quoteId (rolls back the lock).

**Phase 2 — Update meltTokens flow in mint-service.ts:**
```typescript
// 1. Lock proofs as PENDING (replaces atomic spend)
await this.repo.lockProofsAsPending(inputProofs, quote.id);

try {
  // 2. Attempt Lightning payment
  const result = await this.lightning.sendPayment(quote.request);

  // 3. On success: burn proofs permanently
  await this.repo.burnPendingProofs(quote.id);
  await this.repo.updateMeltQuoteState(quote.id, 'PAID');

} catch (err) {
  // 4. On failure: release the lock (proofs are unspent again)
  await this.repo.releasePendingProofs(quote.id);
  await this.repo.updateMeltQuoteState(quote.id, 'UNPAID');
  throw new LightningPaymentError('Payment failed — proofs restored');
}
```

**Double-spend protection:** `lockProofsAsPending` must check both SpentProof AND PendingProof for existing Y-values in the same transaction.

**Saga recovery:** If the process crashes mid-payment (between lock and burn/release), startup or a cron job should query `PENDING` proofs older than TTL and attempt payment status check or release.

## Acceptance Criteria

- [ ] PendingProof model (or state field) added to prisma/schema.prisma
- [ ] `lockProofsAsPending`, `burnPendingProofs`, `releasePendingProofs` added to repository.ts
- [ ] `meltTokens` in mint-service.ts uses two-phase commit flow
- [ ] On Lightning payment failure, proofs are returned to spendable state
- [ ] Double-spend check covers both SpentProof and PendingProof tables
- [ ] Unit test: melt with payment failure leaves proofs unspent
- [ ] Unit test: melt with payment success burns proofs
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P0 blocker) + feature_audit (high severity). This is a fund-loss bug — highest priority fix in the codebase._
