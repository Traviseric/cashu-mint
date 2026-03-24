# Roadmap — @te-btc/cashu-mint

## Phase 1: Core NUTs (4-6 weeks)

Foundation for a working mint that can issue, swap, and melt ecash tokens.

- [x] NUT-00: BDHKE crypto (hash_to_curve, blind/sign/verify with @noble/curves)
- [x] NUT-01: Keyset derivation from seed, `GET /v1/keys`
- [x] NUT-02: Keyset management + rotation, `GET /v1/keysets`
- [x] NUT-03: Swap — double-spend check, atomic spend+sign, saga recovery
- [x] NUT-04: Mint tokens — Lightning invoice generation, quote state machine, blind signing on settlement
- [x] NUT-05: Melt tokens — fee estimation, pending proof hold, LN payment, burn on success
- [x] NUT-06: Mint info endpoint
- [x] NUT-07: Token state check (`POST /v1/checkstate`)
- [x] LND gRPC backend (production Lightning)
- [x] Integration tests against cashu-ts client

## Phase 2: Optional NUTs (2-4 weeks)

Security hardening and advanced features.

- [ ] NUT-08: Lightning fee return (blank output signing for exact change)
- [ ] NUT-10/11: P2PK spending conditions (Schnorr sig verification, multisig, timelocks)
- [ ] NUT-12: DLEQ proofs (prove mint used advertised key)
- [ ] NUT-14: HTLCs (hash timelock contracts for atomic cross-mint swaps)
- [ ] Rate limiting (IP-level + NUT-21 pubkey-level)
- [ ] Input validation hardening (curve point validity, payload size limits)

## Phase 3: Production Hardening (2-3 weeks)

- [ ] NUT-17: WebSocket subscriptions (real-time invoice settlement + state changes)
- [ ] NUT-21/22: Authentication (Clear/Blind auth via OIDC)
- [ ] SpentProof pruning strategy (keyset-based archival)
- [ ] Worker thread offloading for heavy EC math
- [ ] Monitoring, structured logging, health metrics
- [ ] Nutshell CLI interop testing
- [ ] OpenSats grant application

## Phase 4: Programmable eCash — Custom Spending Conditions (Build #2, 2-3 weeks)

Extends the mint with custom condition types beyond NUT-11/14 (which ship in Phase 2). Requires Phase 1+2 working mint as foundation.

Full spec: `../internal/docs/projects/programmable-ecash.md`

### Custom Condition Types
- [ ] Condition router: parse NUT-10 `kind` field → dispatch to registered handler
- [ ] Proof-of-Service (`"PoS"` kind): lock to SHA-256 of expected compute output, deadline + refund tags
- [ ] Multi-party Escrow: 2-of-3 threshold (buyer + seller + arbitrator) via NUT-11 `n_sigs` + `pubkeys`
- [ ] Time-locked Subscriptions: NUT-11 P2PK with `locktime` + `refund` tags
- [ ] Plugin interface: `registerConditionHandler(kind, verifyFn)` for extensibility

### Integration
- [ ] Expose custom condition support via `GET /v1/info` (so wallets/bridges can detect)
- [ ] TokenV4/CBOR serialization with custom condition tags (`cbor-x`)
- [ ] Integration with `@te-btc/cashu-l402` bridge (conditional proof → macaroon with condition caveats)
- [ ] Integration with `@te-btc/agent-wallet` (PoS token generation → provider redemption)
- [ ] Tests for PoS flow: agent mints → provider submits output hash → mint verifies → funds release
- [ ] Tests for escrow flow: 2-of-3 co-sign → release / dispute → arbitrator
- [ ] Tests for time-lock: server time < locktime → only provider redeems / locktime passes → refund keys activate

### Deferred (long-term)
- [ ] STARK/ZK condition detection (NUT-XX PR #288 — experimental, monitor only)
- [ ] Rate-limited redemption (per-period limits, requires ZK accumulators — academic stage)

---

## Dependencies on Other Projects

| This Phase | Needs | Status |
|---|---|---|
| Phase 1-3 | Standalone — no external dependencies | Phase 1 complete |
| Phase 2 (NUT-12 DLEQ) | Enables `@te-btc/cashu-l402` offline verification | Parallel |
| Phase 4 (PoS) | `@te-btc/cashu-l402` for bridge-side PoS flow | Scaffolded |
| Phase 4 (PoS) | `@te-btc/agent-wallet` for agent-side token generation | Planned |
| Phase 4 (programmable eCash spec) | `internal/docs/projects/programmable-ecash.md` | Written |
