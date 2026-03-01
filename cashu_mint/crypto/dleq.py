"""NUT-12: Discrete Log Equality (DLEQ) proofs.

DLEQ proofs allow a wallet to verify offline that the mint used the same
private key ``k`` to produce both its advertised public key ``K = k·G`` and
the blinded signature ``C' = k·B'``.  Without this proof a dishonest mint
could use a user-specific key to de-anonymise token holders.

Protocol (Schnorr sigma, per NUT-12 spec):
─────────────────────────────────────────
  Mint (prover):
    r   ← random scalar
    R1  = r·G
    R2  = r·B'
    e   = SHA-256(R1 ‖ R2 ‖ K ‖ C')   (Fiat–Shamir challenge)
    s   = (r − e·k) mod n

  Wallet (verifier):
    R1  = s·G + e·K
    R2  = s·B' + e·C'
    e'  = SHA-256(R1 ‖ R2 ‖ K ‖ C')
    accept iff e' == e

All point arguments are 33-byte compressed (SEC1) representations.
All scalar arguments / return values use 32-byte big-endian hex strings.

Reference: https://github.com/cashubtc/nuts/blob/main/12.md
"""

from __future__ import annotations

import hashlib

from cashu_mint.crypto.ec import (
    G,
    N,
    bytes_to_point,
    point_add,
    point_to_bytes,
    privkey_to_pubkey,
    random_privkey,
    scalar_mult,
)


def _challenge(
    R1_bytes: bytes,
    R2_bytes: bytes,
    K_bytes: bytes,
    C_prime_bytes: bytes,
) -> int:
    """Fiat–Shamir challenge: e = SHA-256(R1 ‖ R2 ‖ K ‖ C')."""
    digest = hashlib.sha256(R1_bytes + R2_bytes + K_bytes + C_prime_bytes).digest()
    return int.from_bytes(digest, "big"), digest


def generate_dleq_proof(
    B_prime_bytes: bytes,
    C_prime_bytes: bytes,
    k: int,
) -> dict[str, str]:
    """Generate a DLEQ proof that C' = k·B' using the same k as K = k·G.

    Args:
        B_prime_bytes:  33-byte compressed point — wallet's blinded message.
        C_prime_bytes:  33-byte compressed point — mint's blinded signature.
        k:              Mint's private signing key scalar.

    Returns:
        ``{"e": <64-char hex>, "s": <64-char hex>}``
    """
    # Random nonce
    r = random_privkey()

    B_prime = bytes_to_point(B_prime_bytes)
    K_bytes = point_to_bytes(privkey_to_pubkey(k))

    R1 = point_to_bytes(scalar_mult(r, G))       # R1 = r·G
    R2 = point_to_bytes(scalar_mult(r, B_prime))  # R2 = r·B'

    e_int, e_digest = _challenge(R1, R2, K_bytes, C_prime_bytes)

    # s = (r - e·k) mod n
    s = (r - e_int * k) % N

    return {
        "e": e_digest.hex(),
        "s": s.to_bytes(32, "big").hex(),
    }


def verify_dleq_proof(
    B_prime_bytes: bytes,
    C_prime_bytes: bytes,
    K_bytes: bytes,
    e_hex: str,
    s_hex: str,
) -> bool:
    """Wallet-side DLEQ verification.

    Args:
        B_prime_bytes:  33-byte blinded message (wallet-held).
        C_prime_bytes:  33-byte blinded signature from the mint.
        K_bytes:        33-byte mint public key for this denomination.
        e_hex:          Challenge scalar (64-char hex, 32 bytes).
        s_hex:          Response scalar (64-char hex, 32 bytes).

    Returns:
        ``True`` iff the proof is valid.
    """
    try:
        e = int.from_bytes(bytes.fromhex(e_hex), "big")
        s = int.from_bytes(bytes.fromhex(s_hex), "big")

        B_prime = bytes_to_point(B_prime_bytes)
        C_prime = bytes_to_point(C_prime_bytes)
        K = bytes_to_point(K_bytes)

        # R1 = s·G + e·K
        sG = scalar_mult(s, G)
        eK = scalar_mult(e, K)
        R1_pt = point_add(sG, eK)
        if R1_pt is None:
            return False

        # R2 = s·B' + e·C'
        sB = scalar_mult(s, B_prime)
        eC = scalar_mult(e, C_prime)
        R2_pt = point_add(sB, eC)
        if R2_pt is None:
            return False

        R1_bytes = point_to_bytes(R1_pt)
        R2_bytes = point_to_bytes(R2_pt)

        # Recompute challenge and compare
        _, e_computed_digest = _challenge(R1_bytes, R2_bytes, K_bytes, C_prime_bytes)
        return e_computed_digest.hex() == e_hex

    except (ValueError, TypeError):
        return False
