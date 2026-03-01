---
id: 19
title: "Implement NUT-10/11: Spending conditions and Pay-to-Pubkey (P2PK)"
priority: P2
severity: medium
status: pending
source: feature_audit
file: "cashu_mint/nuts/spending_conditions.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: long_running
context_group: core_crypto
group_reason: "Spending conditions extend proof validation in NUT-03 swap and NUT-05 melt — touches crypto and token lifecycle"
---

# Implement NUT-10/11: Spending conditions and Pay-to-Pubkey (P2PK)

**Priority:** P2 (medium)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/spending_conditions.py

## Problem

NUT-10/NUT-11: No spending conditions or P2PK support. Advanced token locking (Pay-to-Pubkey, HTLC) is entirely absent.

Without spending conditions:
- Tokens cannot be locked to a specific recipient (P2PK)
- Atomic swaps and multi-party payment flows are impossible
- The mint cannot enforce conditional spending rules

NUT-10 defines the spending condition framework; NUT-11 defines the P2PK condition specifically.

## How to Fix

Implement spending condition parsing and P2PK verification:

```python
# cashu_mint/nuts/spending_conditions.py
import json
from dataclasses import dataclass
from coincurve import PublicKey

@dataclass
class P2PKCondition:
    pubkey: str         # hex-encoded 33-byte compressed pubkey
    locktime: int | None = None
    n_sigs: int = 1     # threshold signatures required

def parse_spending_condition(secret: str) -> P2PKCondition | None:
    """Parse a NUT-10/11 spending condition from a proof secret."""
    try:
        data = json.loads(secret)
        if not isinstance(data, list) or len(data) < 2:
            return None
        kind = data[0]
        if kind != "P2PK":
            return None
        payload = data[1]
        return P2PKCondition(
            pubkey=payload["data"],
            locktime=payload.get("tags", {}).get("locktime"),
            n_sigs=payload.get("tags", {}).get("n_sigs", 1)
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

def verify_p2pk(secret: str, witness: dict | None) -> bool:
    """Verify P2PK spending condition: witness must contain valid signature."""
    condition = parse_spending_condition(secret)
    if condition is None:
        return True  # No spending condition: regular proof, always valid

    if witness is None:
        raise CashuError(10000, "Proof requires witness (P2PK)")

    signatures = witness.get("signatures", [])
    # Verify at least n_sigs valid secp256k1 signatures
    valid_count = 0
    for sig_hex in signatures:
        if verify_schnorr_signature(sig_hex, condition.pubkey, secret):
            valid_count += 1
    if valid_count < condition.n_sigs:
        raise CashuError(10000, "Insufficient valid P2PK signatures")
    return True
```

Integrate into proof validation in swap and melt:
```python
# In proof validation loop:
spending_cond = parse_spending_condition(proof.secret)
if spending_cond:
    verify_p2pk(proof.secret, proof.witness)
```

Steps:
1. Implement `parse_spending_condition()` for NUT-10 secret format
2. Implement P2PK signature verification per NUT-11
3. Extend `Proof` model with optional `witness` field
4. Integrate condition check into swap and melt proof validation
5. Handle locktime (reject P2PK proofs past locktime)

## Acceptance Criteria

- [ ] P2PK-locked proofs require valid secp256k1 witness signature
- [ ] P2PK proofs without witness rejected with clear error
- [ ] Regular proofs (no spending condition) unaffected
- [ ] Locktime enforced: expired P2PK proofs spendable by anyone after locktime
- [ ] NUT-10 and NUT-11 listed as supported in GET /v1/info

## Notes

_Generated from feature_audit finding: NUT-10/11 Spending Conditions & P2PK (medium, effort: high). Marked long_running due to complexity._
