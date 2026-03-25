# Agent Tasks

## Pending

### Audits (required before SWITCH_PROJECT gate)
- [ ] P0: Run SECURITY_AUDIT — BDHKE crypto correctness, double-spend race conditions, gRPC TLS cert + macaroon credential handling
- [ ] P0: Run UX_AUDIT — NUT spec response format compliance, error code alignment with Cashu protocol spec, /v1/info discoverability

### P1 — Production Gaps
- [x] P1: Extract actual routing fee from LND sendPayment — `src/lightning/lnd.ts:188` hardcodes `fee: 0`; extract `payment_route.total_fees_msat` from SendResponse
- [x] P1: Advertise NUT-08 in SUPPORTED_NUTS — add `'8'` to `src/core/constants.ts` + route validation in melt, or remove partial change-output logic from meltTokens
- [x] P1: Add keyset rotation trigger — `rotateKeyset()` exists in MintService but nothing invokes it; add `POST /v1/admin/rotate-keyset` or `ROTATE_KEYSET_ON_START=true` env config
- [x] P1: Verify LND subscribeInvoices reconnect resilience — `startInvoiceSubscriptionLoop` 5s backoff only tested with FakeWallet; verify TLS/macaroon auth error handling and stream termination recovery

### P2 — Code Quality
- [x] P2: Add runtime guard for LND gRPC package loading — `src/lightning/lnd.ts:49` throws `LightningBackendError` if `lnrpc.Lightning` missing
- [x] P2: Validate DB enum casts for quote state — `assertMintQuoteState()` / `assertMeltQuoteState()` guard functions at top of `mint-service.ts`
- [x] P2: Strengthen MintInfo.nuts typing — `src/core/types.ts:150` now `Record<string, Record<string, unknown>>`
- [ ] P2: Split meltTokens() into sub-methods — 108 lines (423-531); extract `_validateMeltInputs()` and `_executeMeltPayment()`
- [x] P2: Remove @fastify/swagger and @fastify/websocket dead dependencies from package.json — already absent

### P3 — Test Coverage
- [ ] P3: Add LndBackend unit tests — zero coverage for `src/lightning/lnd.ts`; mock gRPC; cover estimateFee, subscribeInvoices, reject-callback fix
- [ ] P3: Add route handler unit tests — only health.test.ts tests routes; add Fastify inject() tests for Zod errors, CashuError, unknown errors
- [ ] P3: Add cashu-ts melt integration test — melt flow not covered in test suite
- [ ] P3: Add config validation tests — `loadConfig()` in `src/utils/config.ts` untested

## Completed
- [x] Melt atomicity two-phase commit (lockProofsAsPending / burnPendingProofs)
- [x] LND gRPC backend: createInvoice, subscribeInvoices, decodePayReq, sendPayment, estimateFee
- [x] Invoice subscription loop with 5s backoff auto-restart
- [x] feeReserve persisted in PendingQuote schema
- [x] NUT-07 PENDING proof state (PendingProof table)
- [x] Melt quote expiry check
- [x] CORS support (@fastify/cors)
- [x] hexPoint Zod validation on B_ and C fields
- [x] cashu-ts integration test suite (6 tests)
- [x] Keyset rotation mechanism (rotateKeyset(), multi-keyset init())
- [x] Fix lnd.ts estimateFee void-reject bug
- [x] Fix getActiveKeyset() plain Error to typed KeysetNotFoundError
- [x] Fix non-null assertion in signOutputs()
- [x] Remove dead getProofStates() export
- [x] Simplify redundant witness ternary patterns
- [x] Implement EstimateRouteFee RPC in lnd.ts
