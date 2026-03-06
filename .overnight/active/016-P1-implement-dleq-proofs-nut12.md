---
id: 16
title: "Implement NUT-12: DLEQ proofs for offline signature verification"
priority: P1
severity: high
status: completed
source: feature_audit
file: "cashu_mint/crypto/dleq.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: core_crypto
group_reason: "DLEQ proofs extend the BDHKE crypto engine (task 2) and are included in blind signature responses"
---

# Implement NUT-12: DLEQ proofs for offline signature verification

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/crypto/dleq.py

## Problem

NUT-12: No DLEQ proofs. Wallets cannot perform offline verification of mint signatures without Discrete Log Equality proofs in mint responses.

Without DLEQ proofs, wallets must trust that the mint signed their tokens correctly. DLEQ proofs allow a wallet to cryptographically verify that the mint used the key it advertised (preventing a dishonest mint from signing with a different key to track users).

## How to Fix

Implement DLEQ proof generation in `cashu_mint/crypto/dleq.py`:

```python
# Discrete Log Equality proof (Schnorr sigma protocol)
# Proves: log_G(K) == log_{B'}(C') without revealing k
# where K = kG (mint public key) and C' = kB' (blind signature)

import os
import hashlib
from coincurve import PrivateKey, PublicKey

def generate_dleq_proof(B_prime: bytes, C_prime: bytes, k: int) -> dict:
    """
    Generate DLEQ proof that C' = k*B' using the same k as K = k*G.

    Returns: {"e": hex, "s": hex}
    """
    G = PublicKey.from_point(
        0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
        0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
    )
    k_bytes = k.to_bytes(32, 'big')

    # Random nonce r
    r_priv = PrivateKey()
    r = int.from_bytes(r_priv.secret, 'big')

    # R1 = r*G, R2 = r*B'
    R1 = PublicKey.from_secret(r_priv.secret)
    B_prime_point = PublicKey(B_prime)
    R2 = B_prime_point.multiply(r_priv.secret)

    # Challenge e = hash(R1 || R2 || K || C')
    K = PublicKey.from_secret(k_bytes)
    e_input = (R1.format(True) + R2.format(True) +
               K.format(True) + PublicKey(C_prime).format(True))
    e = int.from_bytes(hashlib.sha256(e_input).digest(), 'big')

    # s = r - e*k (mod n)
    ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    s = (r - e * k) % ORDER

    return {"e": e.to_bytes(32, 'big').hex(), "s": s.to_bytes(32, 'big').hex()}

def verify_dleq_proof(B_prime: bytes, C_prime: bytes, K_bytes: bytes,
                       e_hex: str, s_hex: str) -> bool:
    """Wallet-side DLEQ verification."""
    # Reconstruct R1 = s*G + e*K, R2 = s*B' + e*C'
    # Then verify e == hash(R1 || R2 || K || C')
    ...  # Implementation follows same pattern as above
```

Integrate DLEQ proofs into blind signature responses (swap, mint):
```python
# In BlindSignature response model:
class BlindSignature(BaseModel):
    amount: int
    id: str
    C_: str
    dleq: dict | None = None  # {"e": hex, "s": hex}
```

Steps:
1. Implement `generate_dleq_proof(B', C', k)` per NUT-12 spec
2. Implement `verify_dleq_proof()` for test coverage
3. Add optional `dleq` field to `BlindSignature` response model
4. Include DLEQ proof in all blind signature responses (swap, mint)
5. Add NUT-12 to supported nuts in GET /v1/info

Reference: https://github.com/cashubtc/nuts/blob/main/12.md

## Acceptance Criteria

- [ ] DLEQ proofs generated for every blind signature response
- [ ] `dleq: {"e": ..., "s": ...}` included in BlindSignature objects
- [ ] Proof is mathematically correct (verifiable by wallet)
- [ ] Unit test: verify_dleq_proof passes with generated proof
- [ ] NUT-12 listed as supported in GET /v1/info

## Notes

_Generated from feature_audit finding: NUT-12 DLEQ Proofs (high)._
