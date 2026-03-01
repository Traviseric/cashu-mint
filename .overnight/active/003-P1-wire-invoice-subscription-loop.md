---
id: 3
title: "Wire invoice subscription loop for backend-agnostic invoice settlement detection"
priority: P1
severity: high
status: completed
source: gap_analyzer
file: src/server.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: lightning_backend
group_reason: "Same Lightning layer as task 002. Should be implemented after LND backend (task 002) to wire the subscription correctly."
---

# Wire invoice subscription loop for backend-agnostic invoice settlement detection

**Priority:** P1 (high — settlement detection broken for production backends)
**Source:** gap_analyzer
**Location:** src/server.ts, src/services/mint-service.ts, src/lightning/interface.ts

## Problem

`ILightningBackend` defines `subscribeInvoices()` returning `AsyncIterable<InvoiceUpdate>`. `FakeWallet` implements it with a working listener queue. However, the server **never calls `subscribeInvoices()`** — invoice settlement is only detected via polling: `getMintQuote` calls `FakeWallet.isSettled()` on each request.

Additionally, `getMintQuote` in `mint-service.ts` (lines 641–662) contains a FakeWallet-specific hack: it extracts a payment hash from a fake bolt11 string by string-slicing and zero-padding, then calls `isSettled()` on the FakeWallet. This code is tightly coupled to FakeWallet's internal format and won't work with a real LND backend.

Current polling hack:
```typescript
// In getMintQuote — FakeWallet-specific detection
const fakeHash = bolt11.slice(-64).padStart(64, '0'); // ← hardcoded FakeWallet format
const settled = (this.lightning as FakeWallet).isSettled(fakeHash);
```

For production LND, invoices would never transition from `UNPAID` to `PAID` without this subscription loop.

## How to Fix

**Step 1 — Remove the FakeWallet polling hack from getMintQuote:**
Replace the FakeWallet-specific `isSettled` detection with a DB-only state check:
```typescript
async getMintQuote(quoteId: string): Promise<MintQuoteResponse> {
  const quote = await this.repo.getMintQuote(quoteId);
  if (!quote) throw new QuoteNotFoundError(quoteId);
  // State is now authoritative from DB — updated by subscription loop
  if (quote.state === 'UNPAID' && Date.now() > quote.expiry * 1000) {
    await this.repo.updateMintQuoteState(quoteId, 'EXPIRED');
    return { ...quote, state: 'EXPIRED' };
  }
  return { quote: quote.bolt11, amount: quote.amount, state: quote.state };
}
```

**Step 2 — Add a background subscription loop in server startup (src/server.ts):**
```typescript
async function startInvoiceSubscriptionLoop(mintService: MintService, lightning: ILightningBackend) {
  try {
    for await (const update of lightning.subscribeInvoices()) {
      if (update.settled && update.paymentHash) {
        await mintService.handleInvoiceSettled(update.paymentHash);
      }
    }
  } catch (err) {
    // Log error and restart after delay (retry loop)
    logger.error('Invoice subscription lost, restarting in 5s:', err);
    setTimeout(() => startInvoiceSubscriptionLoop(mintService, lightning), 5000);
  }
}

// After mintService.init():
startInvoiceSubscriptionLoop(mintService, lightning); // don't await — runs in background
```

**Step 3 — Add `handleInvoiceSettled(paymentHash)` to MintService:**
```typescript
async handleInvoiceSettled(paymentHash: string): Promise<void> {
  const quote = await this.repo.getMintQuoteByPaymentHash(paymentHash);
  if (!quote || quote.state !== 'UNPAID') return;
  await this.repo.updateMintQuoteState(quote.id, 'PAID');
}
```

**Step 4 — Add `getMintQuoteByPaymentHash` to repository.ts:**
Query `PendingQuote` by `paymentHash` field (verify this field exists in prisma/schema.prisma — add it if missing).

## Acceptance Criteria

- [ ] FakeWallet-specific polling hack removed from `getMintQuote`
- [ ] Background `startInvoiceSubscriptionLoop` function added to `src/server.ts`
- [ ] Loop restarts automatically on error with backoff
- [ ] `MintService.handleInvoiceSettled(paymentHash)` method added
- [ ] `getMintQuoteByPaymentHash` added to repository.ts
- [ ] `getMintQuote` reads state purely from DB (no backend-specific calls)
- [ ] FakeWallet `subscribeInvoices()` continues to work for integration tests
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes (FakeWallet tests trigger subscription updates)

## Notes

_Generated from gap_analyzer (P1, blocking=true). Merges the NUT-04 backend-agnostic payment detection finding from feature_audit. This is the subscription plumbing that makes invoice settlement work for any backend._
