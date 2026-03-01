---
id: 5
title: "Implement NUT-01/02: Keyset management and public key endpoints"
priority: P0
severity: critical
status: completed
source: feature_audit
file: "cashu_mint/nuts/keyset.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: keyset_management
group_reason: "NUT-01 and NUT-02 are tightly coupled — both deal with keyset generation and serving public keys"
---

# Implement NUT-01/02: Keyset management and public key endpoints

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/keyset.py

## Problem

NUT-01: No mint public key endpoint exists. Wallets cannot discover the mint's signing keys without GET /v1/keys.

NUT-02: No keyset management exists. GET /v1/keysets and GET /v1/keys/{keyset_id} are absent. No keyset generation, rotation, or fee configuration.

The mint must generate a unique secp256k1 keypair for each denomination (1, 2, 4, 8, 16, ... sats), group them into a keyset, and serve the public keys so wallets can verify signatures and request blind signing.

## How to Fix

1. Implement keyset generation:
```python
# cashu_mint/nuts/keyset.py
from coincurve import PrivateKey, PublicKey
import hashlib

DENOMINATIONS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096,
                 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576,
                 2097152, 4194304, 8388608, 16777216, 32768000]

def derive_keyset_id(keys: dict[int, bytes]) -> str:
    """Derive keyset ID from public keys per NUT-02."""
    # Concatenate sorted public keys, hash, take first 7 bytes
    sorted_keys = b"".join(v for _, v in sorted(keys.items()))
    hash_bytes = hashlib.sha256(sorted_keys).digest()
    version = b"\x00"
    return (version + hash_bytes[:7]).hex()

def generate_keyset(master_key: bytes, unit: str = "sat") -> dict:
    """Generate a keyset with one keypair per denomination."""
    keys = {}
    for i, amount in enumerate(DENOMINATIONS):
        # Derive child key: hash(master_key || amount_index)
        child_key_bytes = hashlib.sha256(master_key + i.to_bytes(4, 'big')).digest()
        priv_key = PrivateKey(child_key_bytes)
        pub_key = priv_key.public_key.format(compressed=True)
        keys[amount] = {"private": child_key_bytes.hex(), "public": pub_key.hex()}
    keyset_id = derive_keyset_id({amt: bytes.fromhex(k["public"]) for amt, k in keys.items()})
    return {"id": keyset_id, "unit": unit, "keys": keys}
```

2. Implement REST endpoints:
```python
# GET /v1/keys → active keyset public keys
# GET /v1/keys/{keyset_id} → public keys for specific keyset
# GET /v1/keysets → list of all keysets (id, unit, active, input_fee_ppk)
```

Response format per NUT-01/02:
```json
{
  "keysets": [{"id": "...", "unit": "sat", "active": true, "input_fee_ppk": 0}]
}
```

Steps:
1. Implement `generate_keyset()` using deterministic key derivation from master key
2. Implement `derive_keyset_id()` per NUT-02 spec
3. Store generated keysets in database on mint startup (if not already present)
4. Implement GET /v1/keys, GET /v1/keys/{keyset_id}, GET /v1/keysets
5. Only return public keys to wallets — never expose private keys via API

## Acceptance Criteria

- [ ] GET /v1/keys returns active keyset public keys in NUT-01 format
- [ ] GET /v1/keysets returns list of keysets in NUT-02 format
- [ ] GET /v1/keys/{keyset_id} returns keys for specific keyset
- [ ] Keyset ID is deterministically derived from public keys per NUT-02
- [ ] Private keys stored in database, never exposed via API
- [ ] Keyset persists across server restarts (loaded from database)

## Notes

_Generated from feature_audit findings: NUT-01 (critical) and NUT-02 (critical). Merged because they share the same keyset data model._
