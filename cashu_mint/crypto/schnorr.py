"""Schnorr signature scheme on secp256k1 used by NUT-11 (P2PK).

This is a deterministic variant of the BIP-340 Schnorr signature without the
x-only public key restriction (we use 33-byte compressed pubkeys throughout).

Signature format: 64 bytes — R.x (32 bytes, big-endian) || s (32 bytes, big-endian)
  where R.y is always even (normalised by negating the nonce if needed).

Signing:
  1. r  = random scalar (or deterministic via RFC-6979 — random used here)
  2. R  = r·G ;  if R.y is odd → negate r so R.y becomes even
  3. e  = SHA-256( R.x || pubkey_bytes || msg )   (all 32/33/len(msg) bytes)
  4. s  = (r + e·privkey) mod n
  5. sig = R.x || s

Verification:
  1. R.x, s  = sig[:32], sig[32:]
  2. e        = SHA-256( R.x || pubkey_bytes || msg )
  3. R'       = s·G − e·P
  4. accept iff  R'.x == R.x  and  R'.y is even
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
    privkey_to_pubkey,
    random_privkey,
    scalar_mult,
)


def schnorr_sign(privkey: int, msg: bytes) -> bytes:
    """Sign *msg* with *privkey* and return a 64-byte Schnorr signature.

    Args:
        privkey: Private key scalar (1 ≤ k < N).
        msg:     Message bytes (any length; commonly 32-byte SHA-256 digest).

    Returns:
        64-byte signature: R.x (32 bytes) || s (32 bytes).
    """
    P = privkey_to_pubkey(privkey)
    P_bytes = point_to_bytes(P)

    while True:
        r = random_privkey()
        R = scalar_mult(r, G)
        assert R is not None
        x_R, y_R = R

        # Normalise: require even y on R  (BIP-340 convention)
        if y_R % 2 != 0:
            r = (N - r) % N
            R = scalar_mult(r, G)
            assert R is not None
            x_R, y_R = R

        R_x = x_R.to_bytes(32, "big")
        e = int.from_bytes(hashlib.sha256(R_x + P_bytes + msg).digest(), "big")
        s = (r + e * privkey) % N

        if s == 0:  # negligible; retry
            continue

        return R_x + s.to_bytes(32, "big")


def schnorr_verify(pubkey_bytes: bytes, msg: bytes, sig: bytes) -> bool:
    """Verify a 64-byte Schnorr signature.

    Args:
        pubkey_bytes: 33-byte compressed secp256k1 public key.
        msg:          Message bytes (must match what was signed).
        sig:          64-byte signature produced by :func:`schnorr_sign`.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
        Never raises; returns ``False`` on any malformed input.
    """
    try:
        if len(sig) != 64:
            return False

        R_x_bytes = sig[:32]
        s = int.from_bytes(sig[32:], "big")
        R_x = int.from_bytes(R_x_bytes, "big")

        if not (0 < s < N):
            return False
        if R_x == 0 or R_x >= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F:
            return False

        P = bytes_to_point(pubkey_bytes)
        e = int.from_bytes(hashlib.sha256(R_x_bytes + pubkey_bytes + msg).digest(), "big")

        # R' = s·G − e·P
        sG = scalar_mult(s, G)
        eP = scalar_mult(e, P)
        R_prime = point_add(sG, point_neg(eP))

        if R_prime is None:
            return False

        x_prime, y_prime = R_prime
        return x_prime == R_x and y_prime % 2 == 0

    except (ValueError, TypeError, AssertionError):
        return False
