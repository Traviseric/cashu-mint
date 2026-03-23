---
id: 2
title: "Add cashu-ts melt integration test"
priority: P3
severity: low
status: completed
source: project_declared
file: src/integration/__tests__/cashu-ts.test.ts
line: 1
created: "2026-03-19T00:10:00"
execution_hint: sequential
context_group: test_coverage
group_reason: "Same integration test file as potential LndBackend tests"
---

# Add cashu-ts melt integration test

**Priority:** P3 (low)
**Source:** project_declared (AGENT_TASKS.md)
**Location:** src/integration/__tests__/cashu-ts.test.ts

## Problem

The cashu-ts integration test suite at `src/integration/__tests__/cashu-ts.test.ts` covers mint quote → pay → mint tokens → swap → NUT-07 checkstate, but the **melt flow is entirely untested**.

Grep confirms: zero matches for "melt" in cashu-ts.test.ts.

This means the full ecash lifecycle (mint → hold tokens → melt back to Lightning) has no end-to-end test coverage. A regression in `meltTokens()`, melt quote handling, or the two-phase commit saga would not be caught by the existing test suite.

## How to Fix

Add a melt integration test to `src/integration/__tests__/cashu-ts.test.ts` using the existing `buildTestServer()` helper and `FakeWallet`.

Test steps:
1. Create a mint quote → simulate payment (FakeWallet.settleInvoice) → mint tokens
2. Get a melt quote via `wallet.getMeltQuote(bolt11)`
3. Execute melt via `wallet.meltTokens(meltQuote, proofs)`
4. Assert: payment succeeded, proofs are spent (NUT-07 checkstate returns SPENT)
5. Assert: change outputs signed (if NUT-08 overpay scenario applies)

The `FakeWallet` supports `settleInvoice(paymentHash)` for simulating payment. Look at existing tests to understand the FakeWallet API and cashu-ts Wallet/Mint client usage patterns.

**Reference existing test structure:**
```typescript
it('should complete full melt flow', async () => {
  // Mint some tokens first
  const { quote, fakeWallet, proofs } = await mintTokens(wallet, mint, fakeWallet, 64);

  // Get a bolt11 invoice to melt into
  const meltBolt11 = await fakeWallet.createMeltInvoice(64);
  const meltQuote = await wallet.getMeltQuote(meltBolt11);

  // Execute melt
  const meltResult = await wallet.meltTokens(meltQuote, proofs);
  expect(meltResult.isPaid).toBe(true);

  // Verify proofs are spent
  const states = await wallet.checkProofsStates(proofs);
  expect(states.every(s => s.state === CheckStateEnum.SPENT)).toBe(true);
});
```

## Acceptance Criteria

- [ ] New `it('should complete full melt flow')` test added to cashu-ts.test.ts
- [ ] Test covers: melt quote creation, token melt, proof spent state verification
- [ ] Test passes against real PostgreSQL (integration test, needs DB)
- [ ] `npm test` passes (including new test with DATABASE_URL set)

## Notes

_Generated from AGENT_TASKS.md P3 pending item. Requires PostgreSQL — run `docker compose up -d` before testing._
