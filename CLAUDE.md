# CLAUDE.md — @te-btc/cashu-mint

## What This Is

TypeScript Cashu mint implementing NUT-00 through NUT-07. Standalone Fastify microservice backed by PostgreSQL + Lightning (LND or FakeWallet). Phase 1 complete — all core NUTs implemented and tested.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Runtime | Node.js 18+ (ES2022) |
| Framework | Fastify 5 |
| Language | TypeScript (ESM, NodeNext) |
| Database | PostgreSQL 16 + Prisma |
| Crypto | @noble/curves, @noble/hashes, @scure/bip32 |
| Lightning | @grpc/grpc-js (LND gRPC) |
| Validation | Zod |
| Testing | Vitest |
| Lint/Format | Biome |
| Package manager | npm |

## File Lookup

| What | Where |
|------|-------|
| Cashu protocol types | `src/core/types.ts` |
| Error codes | `src/core/errors.ts` |
| Constants (denominations, NUTs) | `src/core/constants.ts` |
| BDHKE crypto | `src/core/crypto/bdhke.ts` |
| Keyset derivation | `src/core/crypto/keyset.ts` |
| DB schema | `prisma/schema.prisma` |
| Repository layer | `src/db/repository.ts` |
| Lightning interface | `src/lightning/interface.ts` |
| FakeWallet (test) | `src/lightning/fake-wallet.ts` |
| Route handlers | `src/routes/v1/*.ts` |
| Business logic | `src/services/mint-service.ts` |
| Zod schemas | `src/utils/schemas.ts` |
| Config loader | `src/utils/config.ts` |
| Server entry | `src/server.ts` |
| Test helpers (create proofs) | `src/core/crypto/__tests__/test-helpers.ts` |
| BDHKE unit tests | `src/core/crypto/__tests__/bdhke.test.ts` |
| Keyset unit tests | `src/core/crypto/__tests__/keyset.test.ts` |
| Integration tests | `src/services/__tests__/mint-service.test.ts` |
| Roadmap (phased build plan) | `ROADMAP.md` |
| Programmable eCash spec (Phase 4) | `../internal/docs/projects/programmable-ecash.md` |

## Architecture Rules

1. **ESM only** — all imports use `.js` extensions (NodeNext resolution)
2. **DDD boundaries** — routes call services, services call db/lightning, never skip layers
3. **Prisma for all DB** — no raw SQL except inside Prisma `$executeRaw` for SERIALIZABLE transactions
4. **ILightningBackend** — all Lightning ops go through the interface, never import LND directly in services
5. **Zod at the edge** — validate all incoming request bodies in route handlers before passing to services
6. **Error codes** — use typed CashuError subclasses from `src/core/errors.ts`, never throw plain Error

## Key Patterns

- **hashToCurve API**: `hashToCurve(Uint8Array)` matches the NUT-00 spec (raw bytes). Use `hashToCurveString(secret)` for string secrets — it UTF-8 encodes internally, matching cashu-ts wallet behavior.
- **Saga recovery**: SpentProof + BlindSignature written atomically. On resubmit, match B_ payloads against stored signatures instead of throwing double-spend. Mint saga recovers by quoteId.
- **FakeWallet**: deterministic Lightning backend for testing — no Docker/LND needed for unit tests
- **Keyset rotation**: old keysets stay spendable (redeem) but not issuable (new mints)
- **MintService.init()**: must be called before server starts — derives keyset from seed, upserts in DB, loads into memory
- **NUT-07 checkstate**: queries SpentProof by Y point (hash_to_curve of secret), not by raw secret

## Dev Commands

```bash
npm run dev          # Fastify dev server with tsx watch
npm test             # Vitest (unit tests pass without DB)
npm run typecheck    # tsc --noEmit
npm run lint         # Biome check
npm run db:studio    # Prisma Studio
docker compose up -d # PostgreSQL (needed for integration tests)
npx prisma generate  # Regenerate client after schema changes
npx prisma db push   # Push schema to DB
```

## Phase 1 Status

All NUT-00 through NUT-07 implemented. 33 unit tests passing, 12 integration tests (need PostgreSQL).

Remaining Phase 1 items:
- LND gRPC backend (production Lightning — `src/lightning/lnd.ts` is stubbed)
- Integration tests against cashu-ts client
