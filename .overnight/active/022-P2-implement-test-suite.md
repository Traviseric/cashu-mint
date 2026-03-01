---
id: 22
title: "Implement comprehensive test suite (unit, integration, E2E)"
priority: P2
severity: low
status: pending
source: feature_audit
file: "tests/"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: long_running
context_group: quality
group_reason: "Test suite covers all components — crypto, database, API endpoints, and end-to-end flows"
---

# Implement comprehensive test suite (unit, integration, E2E)

**Priority:** P2 (low)
**Source:** feature_audit / gap_analyzer
**Location:** tests/

## Problem

No test suite exists of any kind. No unit tests for cryptographic primitives, no integration tests for API endpoints, no E2E tests for mint/melt flows.

Without tests:
- Regressions go undetected
- Cryptographic correctness cannot be verified
- The mint cannot be safely deployed to production
- Double-spend logic cannot be validated under concurrent load

## How to Fix

Build a layered test suite:

```python
# tests/unit/test_bdhke.py — Cryptographic correctness
import pytest
from cashu_mint.crypto.bdhke import hash_to_curve, step1_alice, step2_bob, step3_alice, verify

# Known test vectors from NUT-00 spec
NUT00_VECTORS = [
    {
        "secret": "test_message",
        "k": 0x1,  # private key = 1 for test
        "expected_C": "..."  # from spec
    }
]

def test_bdhke_roundtrip():
    """Full BDHKE roundtrip: blind -> sign -> unblind -> verify."""
    from coincurve import PrivateKey
    k = PrivateKey()
    K = k.public_key.format(True)

    B_prime, r = step1_alice("test secret")
    C_prime = step2_bob(B_prime, int.from_bytes(k.secret, 'big'))
    C = step3_alice(C_prime, r, K)
    assert verify("test secret", C, int.from_bytes(k.secret, 'big'))

def test_tampered_signature_fails():
    """Modified signature should not verify."""
    ...

# tests/integration/test_swap.py — API endpoint tests
from fastapi.testclient import TestClient
from cashu_mint.main import app

client = TestClient(app)

def test_swap_valid_tokens():
    """Swap endpoint with valid proofs returns signatures."""
    ...

def test_swap_double_spend_rejected():
    """Same proofs submitted twice: second attempt fails with code 10001."""
    ...

def test_swap_inflation_rejected():
    """Input amount != output amount: rejected."""
    ...

# tests/e2e/test_mint_melt_flow.py — Full flows
def test_full_mint_and_melt():
    """
    E2E: Create mint quote -> pay invoice -> mint tokens ->
    create melt quote -> melt tokens -> verify payment.
    Uses FakeBackend for Lightning.
    """
    ...
```

Steps:
1. Set up pytest with pytest-asyncio for async test support
2. Write unit tests for BDHKE using NUT-00 test vectors
3. Write unit tests for keyset ID derivation
4. Write integration tests for all API endpoints using TestClient
5. Write E2E test for full mint/melt flow with FakeBackend
6. Write concurrency test for double-spend prevention
7. Add pytest configuration to pyproject.toml

## Acceptance Criteria

- [ ] `pytest` passes with 0 failures
- [ ] BDHKE unit tests cover all 5 primitives
- [ ] API tests cover happy path for: /keys, /keysets, /swap, /mint/quote, /mint, /melt/quote, /melt, /info, /checkstate
- [ ] Double-spend E2E test: concurrent requests, only one succeeds
- [ ] Coverage > 70% on cashu_mint/ package
- [ ] Tests run in CI without a real Lightning node (FakeBackend)

## Notes

_Generated from feature_audit finding: Test Suite (low, effort: high)._
