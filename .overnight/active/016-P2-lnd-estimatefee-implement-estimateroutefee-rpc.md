---
id: 16
title: "LND estimateFee: implement EstimateRouteFee RPC instead of 1% hardcoded fallback"
priority: P2
severity: medium
status: completed
source: review_audit
file: src/lightning/lnd.ts
line: 145
created: "2026-02-28T06:00:00Z"
execution_hint: sequential
context_group: lnd_backend
group_reason: "Same file as task 011 (lnd.ts). Both touch LND fee estimation. Do task 011 first."
---

# LND estimateFee: implement EstimateRouteFee RPC instead of 1% hardcoded fallback

**Priority:** P2 (medium — functional but imprecise for production; over/under-charges fee reserve)
**Source:** review_audit (new_tasks finding)
**Location:** src/lightning/lnd.ts:145–160, src/lightning/proto/lightning.proto

## Problem

`LndBackend.estimateFee()` uses a hardcoded `max(1% of amount, 1 sat)` fallback instead of calling LND's `EstimateRouteFee` gRPC RPC. In production, this heuristic can significantly over- or under-estimate routing fees, causing users to either pay too much fee reserve or have melt operations fail due to insufficient fee budget.

The review_audit confirmed: "estimateFee does NOT call EstimateRouteFee — it decodes the invoice then calculates a hardcoded 1%+1sat fallback (line 156). The EstimateRouteFee RPC IS defined in the proto file and the LndClient interface, but it is never called."

**Current code:**
```typescript
async estimateFee(bolt11: string): Promise<number> {
    const decoded = await this.decodePayReq(bolt11);
    // 1% + 1 sat fallback — not using EstimateRouteFee RPC
    return Math.max(Math.ceil(decoded.amount * 0.01), 1);
}
```

**Additionally:** `sendPayment()` hardcodes `fee: 0` in the PaymentResult instead of extracting the actual routing fee paid. This means the fee_reserve collected upfront is never reconciled with the actual fee charged.

## How to Fix

**Step 1 — Extend the proto `DecodePayReq` response to include `destination`:**

Check `src/lightning/proto/lightning.proto`. The `PayReq` message likely has a `string destination` field. If not, add it to the `PayReq` message definition in the local proto.

**Step 2 — Implement `estimateFee` using `EstimateRouteFee`:**

```typescript
async estimateFee(bolt11: string): Promise<number> {
    const decoded = await this.decodePayReq(bolt11);
    // Convert destination pubkey string to bytes for EstimateRouteFee
    const destBytes = Buffer.from(decoded.destination, 'hex');

    return new Promise((resolve, reject) => {
        this.client.EstimateRouteFee(
            {
                dest: destBytes,
                amt_sat: decoded.amount,
            },
            this.metadata,
            (err: Error | null, response: { routing_fee_msat: number }) => {
                if (err) {
                    // Fall back to 1% + 1 sat if RPC fails
                    resolve(Math.max(Math.ceil(decoded.amount * 0.01), 1));
                    return;
                }
                // Convert msat to sat, round up
                resolve(Math.ceil(response.routing_fee_msat / 1000));
            },
        );
    });
}
```

**Step 3 — Extend LndClient interface to include `EstimateRouteFee`:**

Add to the `LndClient` interface at the top of lnd.ts (if not already present):
```typescript
EstimateRouteFee(
    request: { dest: Uint8Array; amt_sat: number },
    metadata: Record<string, string>,
    callback: (err: Error | null, response: { routing_fee_msat: number }) => void
): void;
```

**Step 4 — (Bonus) Fix sendPayment to return actual routing fee:**

If the `SendResponse` proto can be extended with `payment_route.total_fees`, extract the actual fee paid and return it in `PaymentResult.fee` instead of hardcoding 0.

## Acceptance Criteria

- [ ] `estimateFee()` calls `EstimateRouteFee` gRPC RPC when LND is available
- [ ] Falls back gracefully (1% + 1 sat) if `EstimateRouteFee` fails
- [ ] `DecodePayReq` response includes `destination` field (check/extend proto)
- [ ] `EstimateRouteFee` added to `LndClient` interface
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Dependencies

- Complete task 011 first (cleans up dead code in estimateFee — reduces merge conflicts)

## Notes

_Generated from review_audit new_tasks (MEDIUM — worker task 002 claimed "all 5 methods implemented" but estimateFee uses heuristic fallback rather than real RPC). Low-priority for local testing but important for production fee accuracy._
