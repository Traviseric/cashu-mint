"""Unit tests for NUT-00: BDHKE cryptographic engine.

Tests cover:
- hash_to_curve: determinism, NUT-00 spec test vectors
- Full round-trip: blind → sign_blinded → unblind → verify
- Negative cases: tampered signatures, wrong keys
"""

import pytest

from cashu_mint.crypto.bdhke import blind, hash_to_curve, sign_blinded, unblind, verify
from cashu_mint.crypto.ec import (
    G,
    N,
    point_to_bytes,
    privkey_to_pubkey,
    random_privkey,
    scalar_mult,
)

# ---------------------------------------------------------------------------
# NUT-00 official test vectors
# https://github.com/cashubtc/nuts/blob/main/00.md
# ---------------------------------------------------------------------------

# hash_to_curve test vectors
HASH_TO_CURVE_VECTORS = [
    (
        bytes(32),  # 32 zero bytes
        "0266687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925",
    ),
    (
        b"\x00" * 31 + b"\x01",  # 31 zeros + 0x01
        # SHA256(b"\x00"*31+b"\x01") = ec4916dd...c5 is a valid secp256k1 x-coord
        "02ec4916dd28fc4c10d78e287ca5d9cc51ee1ae73cbfde08c6b37324cbfaac8bc5",
    ),
]


class TestHashToCurve:
    def test_deterministic(self) -> None:
        msg = b"test message"
        pt1 = hash_to_curve(msg)
        pt2 = hash_to_curve(msg)
        assert pt1 == pt2

    def test_different_messages_give_different_points(self) -> None:
        assert hash_to_curve(b"msg1") != hash_to_curve(b"msg2")

    def test_returns_valid_curve_point(self) -> None:
        from cashu_mint.crypto.ec import A, B, P

        x, y = hash_to_curve(b"valid test")
        # Check the point satisfies y^2 = x^3 + 7 (mod P)
        assert (y * y) % P == (x * x * x + B) % P

    @pytest.mark.parametrize("message_bytes,expected_hex", HASH_TO_CURVE_VECTORS)
    def test_nut00_vectors(self, message_bytes: bytes, expected_hex: str) -> None:
        pt = hash_to_curve(message_bytes)
        assert point_to_bytes(pt).hex() == expected_hex, (
            f"hash_to_curve({message_bytes!r}) = {point_to_bytes(pt).hex()!r}, "
            f"expected {expected_hex!r}"
        )


class TestBDHKERoundTrip:
    """Full BDHKE protocol round-trip tests."""

    def _mint_keypair(self) -> tuple[int, bytes]:
        k = random_privkey()
        K_bytes = point_to_bytes(privkey_to_pubkey(k))
        return k, K_bytes

    def test_basic_round_trip(self) -> None:
        """blind → sign → unblind → verify must return True."""
        k, K_bytes = self._mint_keypair()
        secret = b"test_secret_1"

        B_prime_bytes, r = blind(secret)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)

        assert verify(secret, C_bytes, k) is True

    def test_round_trip_multiple_secrets(self) -> None:
        k, K_bytes = self._mint_keypair()
        for i in range(5):
            secret = f"secret_{i}".encode()
            B_prime_bytes, r = blind(secret)
            C_prime_bytes = sign_blinded(B_prime_bytes, k)
            C_bytes = unblind(C_prime_bytes, r, K_bytes)
            assert verify(secret, C_bytes, k) is True, f"Failed for secret index {i}"

    def test_tampered_signature_fails(self) -> None:
        """Modifying the unblinded C must fail verification."""
        k, K_bytes = self._mint_keypair()
        secret = b"tamper_test"

        B_prime_bytes, r = blind(secret)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)

        # Flip the last byte of C to simulate tampering
        bad_C = C_bytes[:-1] + bytes([C_bytes[-1] ^ 0xFF])
        assert verify(secret, bad_C, k) is False

    def test_wrong_secret_fails(self) -> None:
        """Verifying with a different secret must fail."""
        k, K_bytes = self._mint_keypair()
        secret = b"original_secret"

        B_prime_bytes, r = blind(secret)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)

        assert verify(b"different_secret", C_bytes, k) is False

    def test_wrong_key_fails(self) -> None:
        """Verifying with a different mint key must fail."""
        k, K_bytes = self._mint_keypair()
        k_wrong = random_privkey()
        secret = b"key_mismatch_test"

        B_prime_bytes, r = blind(secret)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)

        # Verify with wrong key
        assert verify(secret, C_bytes, k_wrong) is False

    def test_blind_with_explicit_r(self) -> None:
        """Using an explicit blinding factor r must produce the same B'."""
        k, K_bytes = self._mint_keypair()
        secret = b"deterministic_blind"
        r = random_privkey()

        B1, r1 = blind(secret, r=r)
        B2, r2 = blind(secret, r=r)

        assert B1 == B2
        assert r1 == r2 == r

    def test_different_r_gives_different_blinded_message(self) -> None:
        """Each blinding of the same secret with a different r yields a different B'."""
        k, K_bytes = self._mint_keypair()
        secret = b"same_secret"
        r1 = random_privkey()
        r2 = random_privkey()
        # Extremely unlikely to collide
        assert r1 != r2

        B1, _ = blind(secret, r=r1)
        B2, _ = blind(secret, r=r2)
        assert B1 != B2

    def test_round_trip_with_known_key(self) -> None:
        """Deterministic test with fixed k and r to catch regression."""
        # Use a simple, small scalar to make the test deterministic
        k = 0x1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF % N
        if k == 0:
            k = 1
        K_bytes = point_to_bytes(privkey_to_pubkey(k))
        secret = b"deterministic_secret"
        r = 0xFEDCBA9876543210FEDCBA9876543210FEDCBA9876543210FEDCBA9876543210 % N
        if r == 0:
            r = 1

        B_prime_bytes, r_out = blind(secret, r=r)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r_out, K_bytes)
        assert verify(secret, C_bytes, k) is True


class TestBDHKEEdgeCases:
    def test_empty_secret(self) -> None:
        k = random_privkey()
        K_bytes = point_to_bytes(privkey_to_pubkey(k))
        B_prime_bytes, r = blind(b"")
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)
        assert verify(b"", C_bytes, k) is True

    def test_long_secret(self) -> None:
        k = random_privkey()
        K_bytes = point_to_bytes(privkey_to_pubkey(k))
        secret = b"x" * 1000
        B_prime_bytes, r = blind(secret)
        C_prime_bytes = sign_blinded(B_prime_bytes, k)
        C_bytes = unblind(C_prime_bytes, r, K_bytes)
        assert verify(secret, C_bytes, k) is True

    def test_invalid_B_prime_raises(self) -> None:
        k = random_privkey()
        with pytest.raises((ValueError, Exception)):
            sign_blinded(b"\x00" * 33, k)
