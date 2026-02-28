# CLAUDE.md — @te-btc/cashu-mint

## What This Is

TypeScript Cashu mint implementing NUT-00 through NUT-07. Standalone Fastify microservice backed by PostgreSQL + Lightning (LND or FakeWallet).

## Tech Stack

| Layer | Choice |
|-------|--------|
| Runtime | Node.js 18+ (ES2022) |
| Framework | Fastify 5 |
| Language | TypeScript (ESM, NodeNext) |
| Database | PostgreSQL 16 + Prisma |
| Crypto | @noble/curves, @noble/hashes |
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
| Full spec (NUTs, arch, crypto, security) | `docs/SPEC.md` |
| Roadmap (phased build plan) | `ROADMAP.md` |
| Research: TS mint architecture (BDHKE, double-spend, LND gRPC) | `docs/research/typescript-cashu-mint-research.md` |
| Research: NUT-10/11/14 spending conditions (Phase 2) | `docs/research/programmable-ecash-research.md` |
| Programmable eCash spec (Phase 4 — PoS, escrow, time-locks) | `../internal/docs/projects/programmable-ecash.md` |

## Architecture Rules

1. **ESM only** — all imports use `.js` extensions (NodeNext resolution)
2. **DDD boundaries** — routes call services, services call db/lightning, never skip layers
3. **Prisma for all DB** — no raw SQL except inside Prisma `$executeRaw` for SERIALIZABLE transactions
4. **ILightningBackend** — all Lightning ops go through the interface, never import LND directly in services
5. **Zod at the edge** — validate all incoming request bodies in route handlers before passing to services
6. **Error codes** — use typed CashuError subclasses from `src/core/errors.ts`, never throw plain Error

## Key Patterns

- **Saga recovery**: SpentProof + BlindSignature written atomically. On resubmit, match B_ payloads against stored signatures instead of throwing double-spend
- **FakeWallet**: deterministic Lightning backend for testing — no Docker/LND needed for unit tests
- **Keyset rotation**: old keysets stay spendable (redeem) but not issuable (new mints)

## Dev Commands

```bash
npm run dev          # Fastify dev server with tsx watch
npm test             # Vitest
npm run typecheck    # tsc --noEmit
npm run lint         # Biome check
npm run db:studio    # Prisma Studio
docker compose up -d # PostgreSQL
```
