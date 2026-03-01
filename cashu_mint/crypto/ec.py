"""Low-level secp256k1 elliptic curve arithmetic.

Pure-Python implementation — no native extensions required.
Suitable for a mint where cryptographic operations are infrequent
relative to I/O; performance is adequate for production-scale usage.
"""

from __future__ import annotations

import hashlib
import os

# ---------------------------------------------------------------------------
# secp256k1 domain parameters (SECG SEC 2, section 2.7.1)
# ---------------------------------------------------------------------------
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A = 0
B = 7
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

INFINITY = None  # Sentinel for the point at infinity


def _modinv(a: int, m: int) -> int:
    """Modular inverse via extended Euclidean algorithm."""
    if a == 0:
        raise ZeroDivisionError("modular inverse of 0 does not exist")
    return pow(a, m - 2, m)  # Fermat's little theorem (m is prime)


def point_add(
    P1: tuple[int, int] | None,
    P2: tuple[int, int] | None,
) -> tuple[int, int] | None:
    """Add two secp256k1 points."""
    if P1 is INFINITY:
        return P2
    if P2 is INFINITY:
        return P1

    x1, y1 = P1
    x2, y2 = P2

    if x1 == x2:
        if y1 != y2:
            return INFINITY  # P + (-P) = O
        # Point doubling
        lam = (3 * x1 * x1 * _modinv(2 * y1, P)) % P
    else:
        lam = ((y2 - y1) * _modinv(x2 - x1, P)) % P

    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def point_neg(pt: tuple[int, int] | None) -> tuple[int, int] | None:
    """Return the additive inverse of a point."""
    if pt is INFINITY:
        return INFINITY
    x, y = pt
    return (x, (-y) % P)


def scalar_mult(k: int, pt: tuple[int, int] | None) -> tuple[int, int] | None:
    """Scalar multiplication using double-and-add (constant-ish time)."""
    k = k % N
    if k == 0 or pt is INFINITY:
        return INFINITY

    result: tuple[int, int] | None = INFINITY
    addend = pt
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result


# Generator point
G: tuple[int, int] = (Gx, Gy)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def point_to_bytes(pt: tuple[int, int]) -> bytes:
    """Compress a point to 33 bytes (SEC1 compressed form)."""
    x, y = pt
    prefix = b"\x02" if y % 2 == 0 else b"\x03"
    return prefix + x.to_bytes(32, "big")


def bytes_to_point(data: bytes) -> tuple[int, int]:
    """Decompress a 33-byte compressed point.

    Raises:
        ValueError: if the x-coordinate has no solution on the curve.
    """
    if len(data) != 33 or data[0] not in (0x02, 0x03):
        raise ValueError("Not a valid compressed secp256k1 point")

    x = int.from_bytes(data[1:], "big")
    y_sq = (pow(x, 3, P) + B) % P
    y = pow(y_sq, (P + 1) // 4, P)  # Tonelli–Shanks shortcut (p ≡ 3 mod 4)

    if pow(y, 2, P) != y_sq:
        raise ValueError(f"x={x!r} does not lie on secp256k1")

    # Choose the right y parity
    parity = data[0] & 1
    if y % 2 != parity:
        y = P - y
    return (x, y)


def privkey_to_pubkey(privkey: int) -> tuple[int, int]:
    """Derive the public key point for a private key scalar."""
    pt = scalar_mult(privkey, G)
    if pt is INFINITY:
        raise ValueError("Private key produces point at infinity")
    return pt  # type: ignore[return-value]


def random_privkey() -> int:
    """Return a cryptographically random private key scalar."""
    while True:
        k = int.from_bytes(os.urandom(32), "big")
        if 1 <= k < N:
            return k


def privkey_from_bytes(data: bytes) -> int:
    """Parse a 32-byte big-endian private key."""
    if len(data) != 32:
        raise ValueError("Private key must be exactly 32 bytes")
    k = int.from_bytes(data, "big")
    if not (1 <= k < N):
        raise ValueError("Private key out of range [1, N-1]")
    return k


def privkey_to_bytes(k: int) -> bytes:
    """Serialize a private key scalar to 32 bytes."""
    return k.to_bytes(32, "big")
