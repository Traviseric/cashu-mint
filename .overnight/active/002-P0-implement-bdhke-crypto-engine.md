---
id: 2
title: "Implement NUT-00: BDHKE cryptographic engine"
priority: P0
severity: critical
status: completed
source: feature_audit
file: "cashu_mint/crypto/bdhke.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: core_crypto
group_reason: "NUT-00 is the foundation for all blind signature operations — NUT-01/02 keyset generation, NUT-03 swap, NUT-04 mint, NUT-05 melt all depend on this"
---

# Implement NUT-00: BDHKE cryptographic engine

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/crypto/bdhke.py

## Problem

NUT-00: No cryptographic engine exists. The foundational Blind Diffie-Hellman Key Exchange (BDHKE) required for all blind signature operations is entirely absent.

The BDHKE protocol is the cryptographic backbone of the entire Cashu mint. Without it:
- The mint cannot issue ecash tokens (blind signing)
- Wallets cannot verify mint signatures (unblinding)
- No token operations (swap, mint, melt) can function

The protocol requires these primitives on secp256k1:
- `hash_to_curve(x)` — deterministically map a byte string to a curve point
- `blind(x, r)` — wallet-side blinding: B' = hash_to_curve(x) + rG
- `sign_blinded(B', k)` — mint-side signing: C' = kB'
- `unblind(C', r, K)` — wallet-side unblinding: C = C' - rK
- `verify(x, C, K)` — mint-side verification: kY == C where Y = hash_to_curve(x)

## How to Fix

Implement `cashu_mint/crypto/bdhke.py`:

```python
from coincurve import PublicKey, PrivateKey
import hashlib

SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def hash_to_curve(message: bytes) -> PublicKey:
    """Hash a message to a secp256k1 curve point (NUT-00 spec)."""
    # Domain separation prefix per NUT-00
    msg_to_hash = b"Secp256k1_HashToCurve_Cashu_" + message
    while True:
        hash_bytes = hashlib.sha256(msg_to_hash).digest()
        try:
            # Try to interpret as compressed point with 0x02 prefix
            point = PublicKey(b'\x02' + hash_bytes)
            return point
        except Exception:
            msg_to_hash = hashlib.sha256(hash_bytes).digest()

def step1_alice(secret_msg: str) -> tuple[bytes, int]:
    """Wallet step 1: blind a secret. Returns (B'_bytes, r)."""
    r = PrivateKey()  # random blinding factor
    Y = hash_to_curve(secret_msg.encode())
    B_prime = Y.combine([PublicKey.from_secret(r.secret)])
    return B_prime.format(compressed=True), int.from_bytes(r.secret, 'big')

def step2_bob(B_prime_bytes: bytes, private_key_k: int) -> bytes:
    """Mint step 2: sign a blinded message. Returns C'_bytes."""
    B_prime = PublicKey(B_prime_bytes)
    k_bytes = private_key_k.to_bytes(32, 'big')
    C_prime = B_prime.multiply(k_bytes)
    return C_prime.format(compressed=True)

def step3_alice(C_prime_bytes: bytes, r: int, K_bytes: bytes) -> bytes:
    """Wallet step 3: unblind the signature. Returns C_bytes (the token)."""
    C_prime = PublicKey(C_prime_bytes)
    K = PublicKey(K_bytes)
    # C = C' - rK
    neg_rK = K.multiply(r.to_bytes(32, 'big')).negate()
    C = C_prime.combine([neg_rK])
    return C.format(compressed=True)

def verify(secret_msg: str, C_bytes: bytes, private_key_k: int) -> bool:
    """Mint verification: check kY == C."""
    Y = hash_to_curve(secret_msg.encode())
    k_bytes = private_key_k.to_bytes(32, 'big')
    expected_C = Y.multiply(k_bytes)
    return expected_C.format(compressed=True) == C_bytes
```

Steps:
1. Implement `hash_to_curve` per NUT-00 specification
2. Implement `step1_alice` (blinding), `step2_bob` (signing), `step3_alice` (unblinding)
3. Implement `verify` for mint-side token verification
4. Write unit tests using known test vectors from NUT-00 spec

Reference: https://github.com/cashubtc/nuts/blob/main/00.md

## Acceptance Criteria

- [ ] `hash_to_curve` produces deterministic, reproducible curve points
- [ ] Full BDHKE round trip works: blind → sign → unblind → verify returns True
- [ ] Tampered signatures fail verification
- [ ] Unit tests pass against NUT-00 test vectors
- [ ] No raw private key bytes exposed in logs or exceptions

## Notes

_Generated from feature_audit finding: NUT-00 BDHKE crypto engine (critical, blocking)._
