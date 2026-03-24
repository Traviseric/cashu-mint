# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 complete: NUT-00 through NUT-07 full Cashu mint implementation
- NUT-08 token swap support
- LND gRPC backend with invoice subscription loop
- LND fee estimation via EstimateRouteFee RPC
- Keyset rotation — load historical keysets on startup
- Two-phase commit for melt to prevent proof loss on payment failure
- CORS support and hex/point validation at edge
- isPending helper and PENDING state integration test (NUT-07)
- cashu-ts wallet integration test suite
- LndBackend unit tests with mocked gRPC client
- cashu-ts melt flow integration test
- AGENTS.md entrypoint contract

### Changed
- Removed dead @fastify/swagger, swagger-ui, websocket dependencies
- Removed dead getProofStates() export (superseded by getProofStatesByY())
- Removed dead void-reject/destBytes/paymentHash code from LND backend

### Fixed
- Exponential backoff for subscribeInvoices reconnect (1s base, 60s cap)
- Runtime guard for gRPC package load failure
- DB enum cast validation for quote states
- MintInfo.nuts typing tightened to `Record<string, Record<string, unknown>>`
- Melt quote expiry check — mirrors getMintQuote behavior
- fee_reserve persistence on melt quotes (stable NUT-05 fee)
- Plain Error throws replaced with typed KeysetNotFoundError
