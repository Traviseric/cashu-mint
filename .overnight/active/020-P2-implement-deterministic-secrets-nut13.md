---
id: 20
title: "Implement NUT-13: Deterministic secret derivation support"
priority: P2
severity: medium
status: completed
source: feature_audit
file: "cashu_mint/nuts/restore.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: parallel
context_group: core_crypto
group_reason: "NUT-13 is primarily a wallet-side spec; the mint mostly needs to be compatible with deterministic secrets in its restore endpoint"
---

# Implement NUT-13: Deterministic secret derivation support

**Priority:** P2 (medium)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/restore.py

## Problem

NUT-13: No deterministic secret derivation. Without BIP-32-style deterministic secrets, wallet recovery from seed phrase is impossible.

NUT-13 defines how wallets derive secrets deterministically from a BIP-32 seed. While this is primarily a wallet-side concern, the mint must:
1. Accept and correctly handle the deterministic secret format
2. Store blind signatures in a way that supports NUT-09 restore (which pairs with NUT-13)

## How to Fix

NUT-13 is largely a wallet-side implementation. The mint's responsibilities are:

1. **Accept NUT-13 formatted secrets in proofs** — these are just strings (the mint doesn't need to verify derivation)

2. **Ensure NUT-09 restore works with NUT-13 secrets** — when a wallet uses deterministic secrets and calls /v1/restore, the mint should be able to re-issue the corresponding blind signatures

3. **Document compatibility** — update GET /v1/info to indicate NUT-13 compatibility

```python
# NUT-13 secret format (handled transparently):
# The secret is a deterministically derived string like:
# "d52f52b71e83d5f25e42d834c3232e1cf1a88c0b3d5f20ae1d5e7a2b1c3f4e7a"
# The mint treats this as any other secret string — no special handling needed
# as long as:
# 1. hash_to_curve(secret) works correctly (it does, for any string)
# 2. NUT-09 restore stores and replays the blind signature correctly

# Verification: ensure the restore endpoint stores outputs keyed by B'
# so wallets can regenerate their B' values and retrieve the signatures
```

Steps:
1. Verify that existing `hash_to_curve()` handles NUT-13 secret format (it should)
2. Verify NUT-09 restore endpoint handles NUT-13 derived secrets correctly
3. Add NUT-13 to the list of supported NUTs in GET /v1/info
4. Add a note in documentation about NUT-13 wallet compatibility
5. Write an integration test: derive deterministic secret, mint tokens, restore tokens

## Acceptance Criteria

- [ ] Proofs with NUT-13 derived secrets accepted and verified correctly
- [ ] NUT-09 restore works for NUT-13 derived secrets
- [ ] NUT-13 listed as supported in GET /v1/info
- [ ] No special code changes needed (verify by inspection + test)

## Notes

_Generated from feature_audit finding: NUT-13 Deterministic Secrets (medium). Primarily wallet-side; mint just needs to be compatible._
