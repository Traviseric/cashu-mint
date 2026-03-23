---
id: 3
title: "Add LndBackend unit tests with mocked gRPC"
priority: P3
severity: low
status: completed
source: project_declared
file: src/lightning/__tests__/lnd.test.ts
line: 1
created: "2026-03-19T00:10:00"
execution_hint: sequential
context_group: test_coverage
group_reason: "Same test_coverage group as melt integration test"
---

# Add LndBackend unit tests with mocked gRPC

**Priority:** P3 (low)
**Source:** project_declared (AGENT_TASKS.md)
**Location:** src/lightning/__tests__/lnd.test.ts (new file)

## Problem

`src/lightning/lnd.ts` has **zero test coverage**. The LndBackend class implements all production Lightning operations (createInvoice, subscribeInvoices, decodePayReq, estimateFee, sendPayment) but none are tested.

This is especially risky because:
- `estimateFee()` now calls EstimateRouteFee RPC with a fallback to 1% + 1 sat
- `sendPayment()` extracts `payment_route.total_fees_msat` for actual fee reporting
- `subscribeInvoices()` manages async queue with error/end stream handling

Bugs in these functions directly affect fund safety (melt operations, fee reserves).

## How to Fix

Create `src/lightning/__tests__/lnd.test.ts` using Vitest with mocked gRPC client.

**Key test cases:**

1. **estimateFee — EstimateRouteFee succeeds**: Mock DecodePayReq → returns amount+destination; mock EstimateRouteFee → returns routing_fee_msat=10000; assert return value is 10 (ceil(10000/1000)).

2. **estimateFee — EstimateRouteFee fails (fallback)**: Mock EstimateRouteFee to call back with an error; assert fallback = Math.max(Math.ceil(amount * 0.01), 1).

3. **sendPayment — success with fee extraction**: Mock SendPaymentSync to return payment_preimage and payment_route.total_fees_msat=5000; assert result.success=true, result.fee=5.

4. **sendPayment — payment_error string**: Mock SendPaymentSync to return payment_error='no_route'; assert result.success=false, result.error='no_route'.

5. **sendPayment — gRPC error**: Mock SendPaymentSync to call back with err; assert rejects with LightningBackendError.

**Mock approach** (inject mock client via constructor, or vi.mock the grpc module):
```typescript
// Create a mock LndClient directly — inject via constructor or monkey-patch
const mockClient = {
  AddInvoice: vi.fn(),
  DecodePayReq: vi.fn(),
  EstimateRouteFee: vi.fn(),
  SendPaymentSync: vi.fn(),
  SubscribeInvoices: vi.fn(),
};
```

Since `LndBackend` constructor requires file paths (TLS cert, macaroon), you may need to:
- Mock `fs.readFileSync` via `vi.mock('node:fs')`
- Mock `@grpc/grpc-js` and `@grpc/proto-loader` to return the mock client
- Or refactor `LndBackend` to accept an optional pre-built client for testing

## Acceptance Criteria

- [ ] New test file `src/lightning/__tests__/lnd.test.ts` created
- [ ] At least 5 test cases covering estimateFee (success + fallback) and sendPayment (success, payment_error, gRPC error)
- [ ] Tests run without real LND/TLS cert/macaroon files
- [ ] `npm test` passes with new tests included
- [ ] `npm run typecheck` passes

## Notes

_Generated from AGENT_TASKS.md P3 pending item. No LND infrastructure required — all gRPC calls must be mocked._
