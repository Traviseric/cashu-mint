---
id: 2
title: "Implement LND gRPC backend — replace all stub throws with real Lightning calls"
priority: P0
severity: critical
status: completed
source: gap_analyzer + feature_audit
file: src/lightning/lnd.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: lightning_backend
group_reason: "Same Lightning layer as task 003 (invoice subscription loop). LND impl must come first."
---

# Implement LND gRPC backend — replace all stub throws with real Lightning calls

**Priority:** P0 (critical — mint cannot process real Lightning payments)
**Source:** gap_analyzer + feature_audit
**Location:** src/lightning/lnd.ts

## Problem

`LndBackend` in `src/lightning/lnd.ts` has all 5 interface methods throwing `'LND backend not implemented — Phase 1'`. The mint is described in `package.json` as a "Production TypeScript Cashu mint — Chaumian ecash backed by Lightning", but no real Lightning backend exists. Only `FakeWallet` (an in-memory test shim) is functional.

Current stub:
```typescript
async createInvoice(amount: number, description: string): Promise<InvoiceResult> {
  throw new Error('LND backend not implemented — Phase 1');
}
// ... same for all other methods
```

The 5 methods required by `ILightningBackend`:
- `createInvoice(amount, description)` → `InvoiceResult`
- `subscribeInvoices()` → `AsyncIterable<InvoiceUpdate>`
- `decodePayReq(paymentRequest)` → `DecodedPayReq`
- `estimateFee(paymentRequest, amount)` → `FeeEstimate`
- `sendPayment(paymentRequest)` → `PaymentResult`

## How to Fix

Implement `LndBackend` using `@grpc/grpc-js` and LND's gRPC API.

**Setup — load proto and create channel:**
```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import * as fs from 'node:fs';

// Load lightning.proto (download from https://github.com/lightningnetwork/lnd/blob/master/lnrpc/lightning.proto)
// Place in src/lightning/proto/lightning.proto
const packageDef = protoLoader.loadSync('src/lightning/proto/lightning.proto', {
  keepCase: true, longs: String, enums: String, defaults: true, oneofs: true,
});
const lnrpc = grpc.loadPackageDefinition(packageDef).lnrpc as any;

// Auth: TLS cert + macaroon
const tlsCert = fs.readFileSync(config.lnd.tlsCertPath);
const sslCreds = grpc.credentials.createSsl(tlsCert);
const macaroon = fs.readFileSync(config.lnd.macaroonPath).toString('hex');
const macaroonMeta = new grpc.Metadata();
macaroonMeta.add('macaroon', macaroon);
const macaroonCreds = grpc.credentials.createFromMetadataGenerator(
  (_args, callback) => callback(null, macaroonMeta)
);
const combined = grpc.credentials.combineChannelCredentials(sslCreds, macaroonCreds);
this.client = new lnrpc.Lightning(`${config.lnd.host}:${config.lnd.port}`, combined);
```

**createInvoice:** Call `AddInvoice` RPC. Return `{ paymentRequest, paymentHash, expiry }`.

**subscribeInvoices:** Call `SubscribeInvoices` streaming RPC. Yield `InvoiceUpdate` objects for settled invoices. Use an `AsyncGenerator` pattern:
```typescript
async *subscribeInvoices(): AsyncIterable<InvoiceUpdate> {
  const stream = this.client.subscribeInvoices({});
  for await (const invoice of stream) {
    if (invoice.state === 'SETTLED') {
      yield { paymentHash: invoice.r_hash.toString('hex'), settled: true, amount: Number(invoice.value) };
    }
  }
}
```

**decodePayReq:** Call `DecodePayReq` RPC. Return `{ amount, description, expiry, paymentHash }`.

**estimateFee:** Call `QueryRoutes` or `EstimateRouteFee` RPC with dest pubkey decoded from the payment request. Return `{ feeReserve }` in sats.

**sendPayment:** Call `SendPaymentSync` RPC. Return `{ preimage, paymentHash, feePaid }`. Throw `LightningPaymentError` on routing failure.

**Config additions needed in src/utils/config.ts:**
```typescript
lnd: z.object({
  host: z.string().default('localhost'),
  port: z.number().default(10009),
  tlsCertPath: z.string(),
  macaroonPath: z.string(), // admin.macaroon
}).optional(), // optional so FakeWallet still works in tests
```

**Install required package:**
```bash
npm install @grpc/proto-loader
```
(Note: `@grpc/grpc-js` is already in package.json)

Download `lightning.proto` from LND repo and place at `src/lightning/proto/lightning.proto`.

## Acceptance Criteria

- [ ] All 5 `ILightningBackend` methods implemented with real gRPC calls
- [ ] `lightning.proto` file added to `src/lightning/proto/`
- [ ] `@grpc/proto-loader` added to package.json dependencies
- [ ] LND config (host, port, tlsCertPath, macaroonPath) added to config loader
- [ ] `LndBackend` used when `LIGHTNING_BACKEND=lnd` env var is set; FakeWallet remains default
- [ ] `sendPayment` throws `LightningPaymentError` (from `src/core/errors.ts`) on failure
- [ ] `npm run typecheck` passes
- [ ] `npm test` still passes (FakeWallet tests unaffected)

## Notes

_Generated from gap_analyzer (P0 blocker, blocking=true) + feature_audit (high severity). The mint cannot process real Lightning payments without this._
