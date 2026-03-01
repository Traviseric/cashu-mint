---
id: 5
title: "Implement NUT-07 PENDING proof state for in-flight melt payments"
priority: P1
severity: medium
status: completed
source: gap_analyzer + feature_audit
file: src/services/mint-service.ts
line: 474
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: melt_flow
group_reason: "Same melt flow and PendingProof infrastructure as task 001. Should be done after task 001 which adds the PendingProof model."
---

# Implement NUT-07 PENDING proof state for in-flight melt payments

**Priority:** P1 (medium — NUT-07 spec non-compliance)
**Source:** gap_analyzer + feature_audit
**Location:** src/services/mint-service.ts:474, src/db/repository.ts, prisma/schema.prisma

## Problem

`checkProofState` (NUT-07) only returns `SPENT` or `UNSPENT`. The NUT-07 spec requires a third `PENDING` state for proofs locked in an active in-flight melt quote.

Current behavior: proofs submitted to a melt are atomically burned (task 001 will change this to PENDING), but `checkProofState` has no awareness of the PENDING state at all:

```typescript
// mint-service.ts:474 — only queries SpentProof, no PENDING check
async checkProofState(secrets: string[]): Promise<ProofStateResponse[]> {
  const results = await Promise.all(secrets.map(async (secret) => {
    const Y = pointToHex(hashToCurveString(secret));
    const spent = await this.repo.isSpent(Y);
    return { secret, state: spent ? 'SPENT' : 'UNSPENT' };
  }));
  return results;
}
```

Per NUT-07 spec: a proof that is locked in an active (in-flight) melt quote MUST return `state: 'PENDING'`, not `UNSPENT`. Wallets rely on this to know not to double-spend a proof that is currently being used for a melt.

**Note:** This task depends on task 001 (melt atomicity fix) which adds the `PendingProof` model. If task 001 is done first, the `PendingProof` table already exists and this task simply queries it.

## How to Fix

**Step 1 — Add `isPending(Y: string)` to repository.ts:**
```typescript
async isPending(Y: string): Promise<boolean> {
  const pending = await this.prisma.pendingProof.findFirst({ where: { Y } });
  return pending !== null;
}
```

**Step 2 — Update `checkProofState` in mint-service.ts to check all three states:**
```typescript
async checkProofState(secrets: string[]): Promise<ProofStateResponse[]> {
  return Promise.all(secrets.map(async (secret) => {
    const Y = pointToHex(hashToCurveString(secret));
    const spent = await this.repo.isSpent(Y);
    if (spent) return { secret, state: 'SPENT' as const };
    const pending = await this.repo.isPending(Y);
    if (pending) return { secret, state: 'PENDING' as const };
    return { secret, state: 'UNSPENT' as const };
  }));
}
```

**Step 3 — Verify `ProofState` type in src/core/types.ts includes 'PENDING':**
The `ProofState` type already includes `'PENDING'` per the gap_analyzer finding. If not, add it:
```typescript
export type ProofState = 'UNSPENT' | 'PENDING' | 'SPENT';
```

**Step 4 — Update NUT-07 in SUPPORTED_NUTS (src/core/constants.ts):**
Confirm NUT-07 is advertised with all three states supported.

## Acceptance Criteria

- [ ] `isPending(Y: string)` added to repository.ts
- [ ] `checkProofState` checks SPENT → PENDING → UNSPENT in order
- [ ] `ProofState` type includes `'PENDING'`
- [ ] Proofs locked in a melt (PendingProof table) return `state: 'PENDING'`
- [ ] Unit test: proof in PendingProof table returns PENDING state
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Dependencies

- Task 001 (melt atomicity fix) should be completed first — it adds the `PendingProof` model that this task queries.

## Notes

_Generated from gap_analyzer (P1) + feature_audit (medium severity). Depends on task 001's PendingProof infrastructure._
