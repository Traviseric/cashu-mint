## Tasks: 011–016 (batch)
- **011**  — lnd.ts: remove void-reject/destBytes/paymentHash dead code
- **012**  — mint-service.ts: getActiveKeyset() uses KeysetNotFoundError (prior session)
- **013**  — mint-service.ts: signOutputs() null check with KeysetNotFoundError (prior session)
- **014**  — repository.ts: remove dead getProofStates() export (prior session)
- **015**  — mint-service.ts: simplify witness ternaries; repository.ts patterns retained (Prisma null guard)
- **016**  — lnd.ts: implement EstimateRouteFee RPC + destination field in DecodePayReq type
- All 33 unit tests passing, typecheck clean.

## Task: 014-P2-remove-dead-getproofstates-export.md
- **Status:** COMPLETE
- **Changes:** src/db/repository.ts
- **Commit:** f8f9622
- **Notes:** Removed dead `getProofStates()` function (14 lines) from repository.ts. Confirmed no callers exist anywhere in src/ via grep. `getProofStatesByY()` remains untouched. Eliminates ambiguity about which checkstate function to use.

## Task: 010-P1-implement-keyset-rotation-mechanism.md
- **Status:** COMPLETE
- **Changes:** prisma/schema.prisma, src/db/repository.ts, src/services/mint-service.ts
- **Commit:** 7e04a11
- **Notes:** Added `derivationIndex` to Keyset schema, regenerated Prisma client, updated `getAllKeysets()` to order by derivation index, updated `createKeyset()` to accept `derivationIndex`. Rewrote `MintService.init()` to load ALL historical keysets from DB (not just create index 0). Added `rotateKeyset()` public method and `_createNewKeyset()` private helper. All 33 unit tests still passing.
