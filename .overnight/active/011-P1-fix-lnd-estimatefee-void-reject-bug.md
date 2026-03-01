---
id: 11
title: "Fix LndBackend.estimateFee — remove void reject/destBytes/paymentHash dead code"
priority: P1
severity: high
status: completed
source: code_quality_audit
file: src/lightning/lnd.ts
line: 154
created: "2026-02-28T06:00:00Z"
execution_hint: sequential
context_group: lnd_backend
group_reason: "Same file as task 016. Both touch LND fee estimation logic in lnd.ts."
---

# Fix LndBackend.estimateFee — remove void reject/destBytes/paymentHash dead code

**Priority:** P1 (high — silent error suppression bug)
**Source:** code_quality_audit
**Location:** src/lightning/lnd.ts:148–191

## Problem

`LndBackend.estimateFee()` at lnd.ts:154 creates a `Promise` with a `reject` callback that is immediately discarded via `void reject`. The promise can **never reject** — if any error occurs in fee calculation, the promise will hang indefinitely or silently resolve with a stale value. This prevents callers from detecting fee estimation failures.

Additionally, two dead variables add confusion in a security-critical path:
1. `destBytes` (lnd.ts:148) — computed from `decoded.paymentHash` bytes (not the destination pubkey as the comment claims), then immediately discarded with `void destBytes`.
2. `paymentHash` (lnd.ts:184–191) — decoded from `response.payment_hash` in `sendPayment()` then discarded with `void paymentHash`.

**Code with issues:**
```typescript
// lnd.ts:145–160
async estimateFee(bolt11: string): Promise<number> {
    const decoded = await this.decodePayReq(bolt11);
    const destBytes = Buffer.from(decoded.paymentHash, 'hex');
    // ...
    void destBytes; // unused — using fallback below   ← dead variable

    return new Promise((resolve, reject) => {
        const feeReserve = Math.max(Math.ceil(decoded.amount * 0.01), 1);
        void reject; // suppress unused warning         ← REAL BUG: promise can never reject
        resolve(feeReserve);
    });
}

// lnd.ts:184–191
const paymentHash = Buffer.from(response.payment_hash).toString('hex');
void paymentHash;  // ← dead variable
```

## How to Fix

**Fix 1 — estimateFee (P1 bug):** Convert to async/await. Remove the unnecessary `Promise` constructor entirely since `decodePayReq` is already async:

```typescript
async estimateFee(bolt11: string): Promise<number> {
    const decoded = await this.decodePayReq(bolt11);
    // Use a safe fee reserve: max(1% of amount, 1 sat)
    return Math.max(Math.ceil(decoded.amount * 0.01), 1);
}
```

**Fix 2 — dead destBytes:** Remove the `destBytes` variable and its comment entirely. It served no purpose.

**Fix 3 — dead paymentHash in sendPayment:** Remove the `paymentHash` variable declaration and `void paymentHash`. If payment hash validation is needed in the future, implement it; otherwise delete.

## Acceptance Criteria

- [ ] `estimateFee()` no longer uses a `new Promise()` wrapper — errors propagate naturally
- [ ] `void reject` suppression removed
- [ ] `destBytes` dead variable removed from `estimateFee()`
- [ ] `paymentHash` dead variable removed from `sendPayment()`
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from code_quality_audit (3 findings in lnd.ts merged: void reject bug HIGH + destBytes dead code MEDIUM + paymentHash dead code MEDIUM)._
