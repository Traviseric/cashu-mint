---
id: 9
title: "Add integration test suite using cashu-ts wallet client"
priority: P1
severity: medium
status: completed
source: gap_analyzer + feature_audit
file: src/services/__tests__/mint-service.test.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: long_running
context_group: cashu_ts_tests
group_reason: "Independent from other task groups. Requires multiple build-test-fix cycles and cashu-ts protocol discovery."
---

# Add integration test suite using cashu-ts wallet client

**Priority:** P1 (medium — wallet interoperability unverified)
**Source:** gap_analyzer + feature_audit
**Location:** src/services/__tests__/mint-service.test.ts (new file: src/integration/__tests__/cashu-ts.test.ts)

## Problem

Integration tests against a cashu-ts wallet client are listed as a remaining Phase 1 item in ROADMAP.md but are completely absent. There is no `cashu-ts` dependency in `package.json`. Existing integration tests use manual BDHKE unblinding (calculating blind signatures by hand) rather than a real wallet client.

This means real-world wallet-to-mint protocol compatibility is completely unverified:
- Token V3/V4 serialization format compatibility
- cashu-ts blind/unblind round-trip interoperability
- NUT-compliant proof serialization (secret format, amount encoding)
- End-to-end: mint → swap → melt flow as a real wallet would do it

## How to Fix

**Step 1 — Add cashu-ts as a dev dependency:**
```bash
npm install --save-dev @cashu/cashu-ts
```

Check the current cashu-ts API (v2+) to understand the `CashuMint` and `CashuWallet` classes.

**Step 2 — Create test file at `src/integration/__tests__/cashu-ts.test.ts`:**

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { CashuMint, CashuWallet, MintQuoteState } from '@cashu/cashu-ts';
import { buildTestServer } from '../test-helpers.js'; // create if needed

describe.skipIf(!process.env.DATABASE_URL)('cashu-ts wallet integration', () => {
  let server: FastifyInstance;
  let mint: CashuMint;
  let wallet: CashuWallet;
  const BASE_URL = 'http://localhost:3338';

  beforeAll(async () => {
    server = await buildTestServer(); // starts mint with FakeWallet
    await server.listen({ port: 3338 });
    mint = new CashuMint(BASE_URL);
    const keys = await mint.getKeys();
    wallet = new CashuWallet(mint, { keys });
  });

  afterAll(() => server.close());

  it('should get mint info', async () => {
    const info = await mint.getInfo();
    expect(info.name).toBeDefined();
    expect(info.nuts).toBeDefined();
  });

  it('should complete a mint flow: request quote → pay → receive tokens', async () => {
    const quote = await wallet.createMintQuote(64);
    expect(quote.quote).toBeDefined();
    expect(quote.request).toMatch(/^lnbc/);

    // Simulate FakeWallet payment (mark invoice as paid)
    // This requires exposing a test helper or using FakeWallet.settle()

    const { proofs } = await wallet.mintProofs(64, quote.quote);
    expect(proofs).toHaveLength(6); // 64 = 32+16+8+4+2+2 denominations
    expect(proofs.reduce((sum, p) => sum + p.amount, 0)).toBe(64);
  });

  it('should complete a swap (send tokens)', async () => {
    // First mint some tokens, then swap them
    const { proofs: inputProofs } = await mintProofsHelper(wallet, 32);
    const { send: sentProofs } = await wallet.send(16, inputProofs);
    expect(sentProofs.reduce((sum, p) => sum + p.amount, 0)).toBe(16);
  });

  it('should check proof states via NUT-07', async () => {
    const { proofs } = await mintProofsHelper(wallet, 8);
    const states = await mint.check({ Ys: proofs.map(p => /* compute Y */ p.secret) });
    expect(states.states.every(s => s.state === 'UNSPENT')).toBe(true);
  });
});
```

**Step 3 — Create a `buildTestServer` helper** or reuse the existing test setup pattern from `mint-service.test.ts`. The server needs FakeWallet and a real PostgreSQL connection.

**Step 4 — Handle FakeWallet invoice settlement in tests:**
FakeWallet has `settleInvoice(paymentHash)` or similar — expose this so tests can mark invoices as paid without real Lightning. Alternatively, extend FakeWallet to auto-settle on creation for test mode.

**Step 5 — Add a test script for integration tests:**
```json
// package.json
"test:integration": "DATABASE_URL=$DATABASE_URL vitest run src/integration"
```

## Acceptance Criteria

- [ ] `@cashu/cashu-ts` added as devDependency
- [ ] `src/integration/__tests__/cashu-ts.test.ts` created
- [ ] Tests verify: `getInfo`, `getKeys`, mint quote → tokens flow, swap (send), NUT-07 checkstate
- [ ] Tests skip if `DATABASE_URL` is not set (use `describe.skipIf`)
- [ ] FakeWallet settlement mechanism works in test context
- [ ] All tests pass with `docker compose up -d` (PostgreSQL running)
- [ ] `npm run typecheck` passes

## Notes

_Generated from gap_analyzer (P1, effort=medium) + feature_audit (medium severity). This is long_running since it requires understanding cashu-ts API, building test helpers, and multiple fix cycles._
