"""NUT-00: Blind Diffie-Hellman Key Exchange (BDHKE).

This module implements the core cryptographic protocol used by the Cashu mint
for issuing and verifying ecash tokens.

Protocol overview (NUT-00):

  Wallet (Alice)                             Mint (Bob)
  ──────────────                             ──────────
  secret  = random string
  Y       = hash_to_curve(secret)
  r       = random scalar (blinding factor)
  B'      = Y + rG                  ──B'──►  C' = k·B'
                                    ◄──C'──
  C       = C' - rK               (unblind)
                            Later:
  (present secret, C)       ──────────►      verify: k·hash_to_curve(secret) == C

Reference: https://github.com/cashubtc/nuts/blob/main/00.md
"""

from __future__ import annotations

import hashlib

from cashu_mint.crypto.ec import (
    G,
    N,
    bytes_to_point,
    point_add,
    point_neg,
    point_to_bytes,
    privkey_to_bytes,
    privkey_to_pubkey,
    random_privkey,
    scalar_mult,
)

# ---------------------------------------------------------------------------
# Core primitives
# ---------------------------------------------------------------------------


def hash_to_curve(message: bytes) -> tuple[int, int]:
    """Deterministically map a byte string to a secp256k1 point (NUT-00).

    Algorithm (NUT-00 spec):
      1. msg_to_hash = SHA-256(message)
      2. Try to decode ``\\x02 || msg_to_hash`` as a compressed secp256k1 point.
      3. If the x-coordinate is not on the curve, set msg_to_hash = SHA-256(msg_to_hash)
         and retry.

    The domain separator was intentionally not included here — this matches the
    NUT-00 test vectors and the behaviour of interoperable Cashu implementations.

    Reference: https://github.com/cashubtc/nuts/blob/main/00.md
    """
    msg_to_hash = hashlib.sha256(message).digest()
    while True:
        try:
            return bytes_to_point(b"\x02" + msg_to_hash)
        except ValueError:
            msg_to_hash = hashlib.sha256(msg_to_hash).digest()


def blind(secret: bytes, r: int | None = None) -> tuple[bytes, int]:
    """Wallet step 1 — blind a secret.

    Args:
        secret: The secret token value (will be hashed to a curve point).
        r:      Optional blinding factor scalar; generated randomly if None.

    Returns:
        (B_prime_bytes, r)  where B' = hash_to_curve(secret) + r·G
    """
    if r is None:
        r = random_privkey()

    Y = hash_to_curve(secret)
    rG = scalar_mult(r, G)
    B_prime = point_add(Y, rG)
    if B_prime is None:
        raise ValueError("Blinding produced the point at infinity")
    return point_to_bytes(B_prime), r


def sign_blinded(B_prime_bytes: bytes, k: int) -> bytes:
    """Mint step 2 — sign a blinded message.

    Args:
        B_prime_bytes: 33-byte compressed point (wallet's blinded message).
        k:             Mint's private signing key scalar.

    Returns:
        C_prime_bytes: 33-byte compressed blinded signature C' = k·B'.
    """
    B_prime = bytes_to_point(B_prime_bytes)
    C_prime = scalar_mult(k, B_prime)
    if C_prime is None:
        raise ValueError("Signing produced the point at infinity")
    return point_to_bytes(C_prime)


def unblind(C_prime_bytes: bytes, r: int, K_bytes: bytes) -> bytes:
    """Wallet step 3 — remove the blinding factor.

    Args:
        C_prime_bytes: 33-byte blinded mint signature.
        r:             Blinding factor scalar used in step 1.
        K_bytes:       33-byte mint public key for the denomination.

    Returns:
        C_bytes: 33-byte unblinded signature (the ecash token proof).
        C = C' - r·K
    """
    C_prime = bytes_to_point(C_prime_bytes)
    K = bytes_to_point(K_bytes)
    rK = scalar_mult(r, K)
    neg_rK = point_neg(rK)
    C = point_add(C_prime, neg_rK)
    if C is None:
        raise ValueError("Unblinding produced the point at infinity")
    return point_to_bytes(C)


def verify(secret: bytes, C_bytes: bytes, k: int) -> bool:
    """Mint verification — check that a token proof is valid.

    Returns True iff  k · hash_to_curve(secret) == C.

    Args:
        secret:  The secret token value.
        C_bytes: 33-byte unblinded signature presented by the wallet.
        k:       Mint's private signing key scalar.
    """
    Y = hash_to_curve(secret)
    expected_C = scalar_mult(k, Y)
    if expected_C is None:
        return False
    return point_to_bytes(expected_C) == C_bytes


# ---------------------------------------------------------------------------
# High-level helpers used by keyset management
# ---------------------------------------------------------------------------


def privkey_to_pubkey_bytes(k: int) -> bytes:
    """Return the 33-byte compressed public key for a private key scalar."""
    return point_to_bytes(privkey_to_pubkey(k))
