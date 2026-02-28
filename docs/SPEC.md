# @te-btc/cashu-mint

**Status: Planned** — Build Possibility #1
**Effort: 4–6 weeks core + 2–4 weeks hardening**
**License: MIT**
**Package: `@te-btc/cashu-mint`**

---

## Overview

The first production TypeScript/Node.js Cashu mint. Issues and redeems Chaumian ecash tokens backed by Lightning Network liquidity, implementing NUT-00 through NUT-06 (mandatory) plus high-priority optional NUTs.

**Why it matters:** Every existing production Cashu mint is Python (Nutshell) or Rust (CDK, Moksha). Zero generalized, production-ready TypeScript mint exists for Lightning. The TypeScript/JavaScript community — the largest developer community in the world — has no native mint to deploy.

**Strategic position:**
- Eliminates ArxMint's Nutshell Docker dependency — single Node.js process
- Publishable open source fills a massive ecosystem gap
- Prime candidate for OpenSats infrastructure grants (16th Wave funded CDK and cashu-ts directly)
- Enables custom NUTs (programmable eCash, Build Possibility #2) without waiting for protocol consensus
- Becomes the moat: other circular economy builders need a mint, ours is purpose-built for communities + agents

---

## NUT Compliance Matrix

### Mandatory (NUT-00 through NUT-06)

| NUT | Name | Endpoint | Mint Responsibility |
|-----|------|----------|-------------------|
| 00 | Cryptography & Models | — | Maintain scalar private keys per denomination, receive blinded messages (B_), return blinded signatures (C_) via BDHKE |
| 01 | Mint Public Keys | `GET /v1/keys` | Publish active public keys by denomination. Support keyset rotation — old keys go inactive (spendable, not issuable) |
| 02 | Keysets & Fees | `GET /v1/keysets` | Group keys into versioned keysets derived from public key hash. Maintain relational mapping of all historical keysets |
| 03 | Swap | `POST /v1/swap` | Verify unblinded signatures, check spent-proof DB, atomically mark spent + return new blind signatures |
| 04 | Mint Tokens | `POST /v1/mint/quote/bolt11` | Generate Lightning invoice, track state machine (UNPAID → PAID → ISSUED / EXPIRED), sign blinded messages on settlement |
| 05 | Melt Tokens | `POST /v1/melt/quote/bolt11` | Estimate routing fees, hold proofs in pending state, attempt LN payment, burn proofs on success or release on failure |
| 06 | Mint Info | `GET /v1/info` | Return supported NUTs, version, contact info, operator pubkeys |

### High-Priority Optional

| NUT | Feature | Mint Implication |
|-----|---------|-----------------|
| 07 | Token State Check | `POST /v1/checkstate` — wallet polls to verify proofs are unspent. Critical for multi-device sync and backup restoration |
| 08 | Lightning Fee Return | During melt, if actual routing fee < reserved estimate, sign blank blinded messages to return exact change as ecash |
| 10/11 | P2PK Spending Conditions | Tokens locked to Schnorr pubkey. Mint parses JSON secret, extracts pubkey, verifies Schnorr signature in witness payload |
| 12 | DLEQ Proofs | Discrete Log Equality proof attached to every signature — proves mint used the advertised key, prevents secret tagging |
| 14 | HTLCs | Hash Timelock Contracts for atomic cross-mint swaps. Validate preimage against hash lock before allowing spend |
| 17 | WebSocket Subscriptions | Persistent WebSocket connections pushing real-time invoice settlement and token state changes. Replaces HTTP polling |
| 21/22 | Authentication | Clear/Blind auth via OpenID Connect (e.g., Keycloak). Enables closed-loop or compliance-focused circular economies |

### Spending Conditions Implementation (NUT-10/11/14)

Spending conditions are the prerequisite for programmable eCash (Build Possibility #2). The base mint MUST implement the condition routing pipeline correctly — all custom conditions (proof-of-service, escrow, subscriptions) build on this foundation.

**Condition routing in swap/melt pipeline:**
```
For each input.secret in POST /v1/swap:
  1. JSON.parse(secret) → if valid NUT-10 array, route by kind
  2. "P2PK" → NUT-11 validator | "HTLC" → NUT-14 validator | custom → extensible
  3. If not valid JSON → standard unconditional secret
  4. Verify C = k * hash_to_curve(secret) regardless of condition
  5. Check spent-proof DB → atomically mark spent + issue new sigs
```

**NUT-11 P2PK implementation requirements:**
- Schnorr signature verification via `@noble/curves` secp256k1 (64-byte libsecp256k1 format)
- **SIG_ALL aggregation:** Signature commits to all inputs (secret + C) and all outputs (amount + B_). For melt, append blank outputs and `quote_id`. Prevents output substitution by malicious actors
- **Multisig (N-of-M):** Verify each witness signature, extract recovered public key, confirm `n_sigs` **unique** keys from authorized set. Naive signature counting is exploitable — single key produces infinite valid sigs due to auxiliary randomness
- **Timelocks:** `locktime` tag (Unix timestamp). Active lock → only primary key. Expired → refund keys activate. Mint MUST NTP-sync and expose current time via API

**NUT-14 HTLC implementation:**
- Validate preimage against SHA-256 hashlock in secret `data` field
- Enforce timelock fallback on expiry
- Foundation for cross-mint atomic swaps

**Critical correctness: JSON secret parsing.**
`Proof.secret` arrives as escaped JSON string within HTTP JSON payload. The mint must extract the raw, unescaped string exactly as the wallet constructed it before hashing for signature verification. Any encoding/whitespace deviation alters the hash — valid signatures get rejected. This is the primary interoperability failure mode. Test exhaustively against cashu-ts and Nutshell client outputs.

See [`programmable-ecash.md`](programmable-ecash.md) for custom condition extensions (PoS, escrow, subscriptions) built on this foundation.

---

## Architecture

### Standalone Microservice (NOT embedded in Next.js)

Embedding mint logic in Next.js API routes is not viable for production:
- Next.js aggressively terminates long-lived connections (serverless model kills gRPC streams and WebSockets)
- Intensive secp256k1 scalar cryptography blocks the event loop — needs worker thread offloading

**Framework:** Standalone Node.js service using **Fastify** or **Hono**. Fastify provides highest routing throughput in Node ecosystem, native JSON Schema validation (critical for rejecting malformed blinded messages), and optimized WebSocket support. The Next.js frontend communicates with this service over HTTP.

### Project Structure (DDD)

Mirrors CDK's modular crate structure:

```
src/
├── core/        # Protocol constants, error codes, BDHKE math wrappers (@noble/curves)
├── db/          # Prisma schemas, migrations, repository patterns
├── lightning/   # Backend provider interfaces (LND, CLN, FakeWallet)
├── routes/      # Fastify controllers mapping to Cashu REST endpoints (/v1/keys, /v1/swap, etc.)
├── services/    # Core business logic — saga patterns, quote state machines
└── utils/       # Parsers, validators, DLEQ generators
```

### ILightningBackend Provider Interface

Abstract the Lightning backend so operators can swap LND for CLN, LDK Node, LNbits, or Strike without rewriting core state machines. Pattern follows CDK's backend abstraction.

```typescript
interface ILightningBackend {
  createInvoice(amount: number, memo: string): Promise<Bolt11Invoice>;
  subscribeInvoices(): AsyncIterable<InvoiceUpdate>;
  decodePayReq(bolt11: string): Promise<DecodedInvoice>;
  estimateFee(bolt11: string): Promise<number>;
  sendPayment(bolt11: string, feeLimit: number): Promise<PaymentResult>;
}
```

### OpenAPI / Type Safety

Fastify-swagger for OpenAPI conformance against Cashu standard API specs. Zod or TypeBox validators at the network edge to reject invalid BOLT11 strings or improper curve coordinates immediately.

---

## Crypto Implementation

### BDHKE Flow

The Blind Diffie-Hellman Key Exchange is the core of Cashu's blind signature scheme:

1. **Mint Setup** — Generate private scalar `k` per denomination in keyset. Publish `K = k * G`
2. **User Blinding** — User maps secret `x` to curve point `Y = hash_to_curve(x)`, generates blinding factor `r`, sends `B_ = Y + r * G`
3. **Mint Signing** — Mint computes `C_ = k * B_` (cannot derive Y or x due to blinding). Returns `C_`
4. **User Unblinding** — User computes `C = C_ - r * K`, yielding `C = k * Y`
5. **Mint Verification** — On redeem, user presents `(x, C)`. Mint computes `Y = hash_to_curve(x)`, verifies `C == k * Y`

### Dependency Chain

| Package | Role |
|---------|------|
| `@noble/curves` (v1.x+) | Audited pure-TS secp256k1. ProjectivePoint math for B_ and C_ calculations. Schnorr verification for NUT-11 P2PK |
| `@noble/hashes` | SHA-256 for hash_to_curve domain separator derivations |
| `@cashu/crypto` (v0.3.4) | Low-level BDHKE wrapper. Use for reference but interface directly with @noble/curves for production throughput and batch parallelization |

### Implementation Gotchas

1. **Endianness & serialization** — secp256k1 points serialize to compressed 33-byte hex. Never mix `Number` with `BigInt` during scalar arithmetic — strict `bigint` typing is mandatory to prevent precision loss
2. **hash_to_curve** — Cashu mandates domain separator `Secp256k1_HashToCurve_Cashu_` and appends an incrementing `uint32` counter in **little-endian** byte order until a valid x-coordinate on the curve is found. Wrong counter format = incompatible tokens
3. **Key derivation** — Private keys derived deterministically from master seed via BIP-32 path convention using keyset ID as index. Recovering master seed recovers all historical denominations across all epochs

---

## Database Architecture

### PostgreSQL + Prisma (required)

SQLite locks the entire database file on concurrent writes (even in WAL mode) — unacceptable for simultaneous swaps. PostgreSQL handles row-level locking with SERIALIZABLE isolation.

### Core Tables

**1. Keyset**
- `id` (String, PK) — derived Base64 ID
- `active` (Boolean) — can sign new tokens
- `unit` (String) — asset type (`sat`, `msat`, `usd`)

**2. SpentProof (the core ledger)**
- `secret` (String, PK) — plaintext secret `x`. UNIQUE index enforces double-spend prevention at the DB engine level
- `amount` (Integer)
- `keyset_id` (String, FK → Keyset)
- `witness` (JSON) — P2PK signatures or HTLC preimages

**3. PendingQuote**
- `id` (String, PK)
- `request` (String) — BOLT11 invoice
- `state` (Enum) — UNPAID | PAID | PENDING | EXPIRED
- `type` (Enum) — MINT | MELT

**4. BlindSignature**
- Tracks all issued `C_` values
- Critical for Merkle Sum Sparse Merkle Trees (MSSMT) — enables cryptographic proof-of-liabilities for auditing

### Concurrency: SERIALIZABLE Isolation

Node.js async event loop means concurrent HTTP requests can attempt to swap the same proof simultaneously. Without strict transactional boundaries, both requests find the token unspent and issue new tokens — unbacked inflation. SERIALIZABLE isolation level or strict UNIQUE constraints with rollback on duplicate insertion prevents this.

### Saga Pattern for Crash Recovery

Adopted from CDK v0.15.0's "Wallet Sagas." Solves the scenario where Node.js crashes after writing SpentProof but before delivering blind signatures — user's tokens are burned but they received nothing.

**Resolution:** Atomically write SpentProof + IssuedPromise (the generated `C_` values) in the same transaction. If client connection drops, client resubmits identical blinded messages. Mint sees secret already spent, matches `B_` payloads against stored IssuedPromise, returns the already-generated `C_` values instead of throwing double-spend error.

### Pruning Strategy

High-volume mints see linear growth in SpentProof. Keyset rotation (NUT-02) enables pruning: once an old keyset is fully deprecated and all users migrated, archive and prune SpentProof records for that keyset.

---

## Lightning Integration

### LND gRPC via `@grpc/grpc-js`

**Connection:** Authenticate with TLS certificate + admin Macaroon. Read Macaroon from filesystem, convert to hex, inject as gRPC Call Metadata. Combine SSL credentials with metadata generator.

**Environment variable required:** `GRPC_SSL_CIPHER_SUITES='HIGH+ECDSA'` for TLS handshake compatibility with newer LND versions.

### Required RPCs

| Operation | RPC | Purpose |
|-----------|-----|---------|
| Mint (NUT-04) | `AddInvoice` | Generate BOLT11 string |
| Mint (NUT-04) | `SubscribeInvoices` | Persistent stream for instant settlement detection → WebSocket push to client |
| Melt (NUT-05) | `DecodePayReq` | Validate user's requested invoice |
| Melt (NUT-05) | `EstimateFee` | Calculate max routing fee for reserve |
| Melt (NUT-05) | `SendPaymentV2` | Route payment, burn proofs on successful preimage return |

### Why gRPC over REST

gRPC supports persistent bidirectional streaming — essential for pushing instant NUT-17 WebSocket notifications on invoice settlement. REST would require inefficient short-polling.

---

## Security Threat Model

Five attack vectors identified in research, with mitigations:

| # | Attack | Vector | Mitigation |
|---|--------|--------|------------|
| 1 | Token Forgery | Submit B_ coordinates not on secp256k1 curve → leak data or crash | Call `Point.assertValidity()` before any scalar multiplication |
| 2 | Preimage Exhaustion | Unbounded preimages in NUT-14 HTLCs fill database/disk with arbitrary data | Enforce strict payload size limits (< 1024 bytes) on all secret fields |
| 3 | Routing Manipulation | Malicious melt to own node with manipulated routing hints to siphon fee reserves | Strict upper bound on fee reserves (1–2% of payment), auto-fail on excess |
| 4 | Proof Flooding (DoS) | Spam /swap with valid zero-value blinded messages to exhaust CPU on EC math | Rate limiting at IP level (or NUT-21 Nostr pubkey level) via Redis |
| 5 | Double-Spend Races | Concurrent requests swap same proof simultaneously | SERIALIZABLE DB isolation + row-level locking (see Database Architecture) |

### Key Compromise & Rotation

If active private keys (`k`) are extracted from memory, attacker can issue infinite valid ecash.

**Mitigations:**
- Never store private keys in plain text. Derive dynamically from BIP-39 master seed loaded via restricted env vars or secure enclave (AWS KMS, HashiCorp Vault)
- NUT-01 keyset rotation: expose secure admin API to force rotation. On suspected compromise, mark keyset inactive (halts new issuance), monitor swap endpoints for unusual volume

---

## Testing Strategy

No standalone automated CI conformance tool exists for mints. Correctness verified by:

1. **cashu-ts test suite** — Run mint backend against the exhaustive tests in the cashu-ts repository
2. **Nutshell CLI interop** — Establish bidirectional interoperability with the Nutshell client CLI
3. **testnut.cashu.space** — Validate edge-case handling against the known-good reference environment
4. **FakeWallet backend** — `ILightningBackend` implementation returning deterministic responses for unit tests without requiring a live LND node

---

## Open Source & Grants

- **License:** MIT (matches Nutshell, CDK, cashu-ts)
- **Package:** `@te-btc/cashu-mint` on npm
- **Grant target:** OpenSats infrastructure grants — "we built the first production TypeScript Cashu mint" fills the largest gap in the ecosystem
- **Differentiation:**
  - Cloud-native / serverless-ready (Node.js appeals to Vercel, Lambda, Cloudflare deployments)
  - Extensible via Fastify middleware (operators inject custom gating logic — L402 tokens, Nostr interactions)
  - Management API compatible with orchard dashboard

---

## Key Dependencies

| Package | Version | Role |
|---------|---------|------|
| `@noble/curves` | v1.x+ | Audited secp256k1 EC math, Schnorr verification |
| `@noble/hashes` | latest | SHA-256/512 |
| `@cashu/crypto` | v0.3.4 | BDHKE reference implementation |
| `@grpc/grpc-js` | latest | LND gRPC client |
| `@grpc/proto-loader` | latest | LND proto file loading |
| `fastify` | latest | HTTP framework |
| `fastify-websocket` | latest | NUT-17 WebSocket support |
| `prisma` | latest | Type-safe PostgreSQL ORM |
| `zod` | latest | Runtime schema validation |

---

## Effort Estimate

| Phase | Scope | Time |
|-------|-------|------|
| Core mint | NUT-00 through NUT-07, BDHKE, PostgreSQL schema, LND integration, basic swap/mint/melt | 4–6 weeks |
| Hardening | Double-spend edge cases, rate limiting, saga crash recovery, NUT-08/12, error handling | 2–4 weeks |
| **Total** | **Production-ready mint** | **6–10 weeks** |

Validated by research analysis and BUILD_POSSIBILITIES.md. The mint core is estimated at ~1500 lines of TypeScript. ArxMint already provides LND gRPC wiring, PostgreSQL + Prisma setup, rate limiting middleware, and structured logging.

---

## References

- **Research:** [`internal/docs/BUILD_POSSIBILITIES/research/1-TypeScript Cashu Mint Research.md`](../BUILD_POSSIBILITIES/research/1-TypeScript%20Cashu%20Mint%20Research.md) — 343 lines, 36+ citations, exhaustive architectural blueprint
- **Build Possibilities:** [`internal/docs/BUILD_POSSIBILITIES/BUILD_POSSIBILITIES.md`](../BUILD_POSSIBILITIES/BUILD_POSSIBILITIES.md) — strategic context, effort estimates, build order
- **Cashu NUT Specifications:** https://cashubtc.github.io/nuts/
- **cashu-ts:** https://github.com/cashubtc/cashu-ts
- **CDK (reference architecture):** https://github.com/cashubtc/cdk
- **@cashu/crypto:** https://www.npmjs.com/package/@cashu/crypto
