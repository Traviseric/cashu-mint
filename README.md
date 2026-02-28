# @te-btc/cashu-mint

Production TypeScript Cashu mint — Chaumian ecash tokens backed by Lightning Network liquidity.

## What

The first production TypeScript/Node.js implementation of the [Cashu protocol](https://cashubtc.github.io/nuts/). Issues and redeems blind-signed ecash tokens via BDHKE (Blind Diffie-Hellman Key Exchange), with Lightning Network as the settlement layer.

## NUT Compliance

| NUT | Name | Status |
|-----|------|--------|
| 00 | Cryptography & Models | Scaffolded |
| 01 | Mint Public Keys | Scaffolded |
| 02 | Keysets & Fees | Scaffolded |
| 03 | Swap | Scaffolded |
| 04 | Mint Tokens (bolt11) | Scaffolded |
| 05 | Melt Tokens (bolt11) | Scaffolded |
| 06 | Mint Info | Scaffolded |
| 07 | Token State Check | Scaffolded |

## Quick Start

```bash
# Install dependencies
npm install

# Start dev PostgreSQL
docker compose up -d

# Generate Prisma client + push schema
npx prisma generate
npx prisma db push

# Run dev server (FakeWallet backend)
cp .env.example .env
npm run dev

# Run tests
npm test
```

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start dev server with hot-reload |
| `npm run build` | Compile TypeScript to dist/ |
| `npm start` | Run compiled server |
| `npm run typecheck` | Type-check without emitting |
| `npm test` | Run test suite |
| `npm run lint` | Lint with Biome |
| `npm run db:studio` | Open Prisma Studio |

## Architecture

Standalone Fastify microservice with DDD structure:

```
src/
├── core/        # Protocol types, constants, BDHKE crypto
├── db/          # Prisma client + repository patterns
├── lightning/   # Backend interface (LND, FakeWallet)
├── routes/      # Fastify route handlers (v1 Cashu API)
├── services/    # Business logic (MintService)
└── utils/       # Zod schemas, config loader
```

## License

MIT
