"""Unit tests for NUT-12: DLEQ proofs.

Tests cover:
- generate_dleq_proof produces valid proofs
- verify_dleq_proof accepts valid proofs
- verify_dleq_proof rejects tampered proofs (wrong B', C', K, e, s)
- sign_blinded_with_dleq integration
- /v1/info advertises NUT-12
"""

from __future__ import annotations

import pytest

from cashu_mint.crypto.bdhke import blind, sign_blinded, sign_blinded_with_dleq
from cashu_mint.crypto.dleq import generate_dleq_proof, verify_dleq_proof
from cashu_mint.crypto.ec import (
    point_to_bytes,
    privkey_to_pubkey,
    random_privkey,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_keypair() -> tuple[int, bytes]:
    """Return (k, K_bytes) for a random mint key."""
    k = random_privkey()
    K_bytes = point_to_bytes(privkey_to_pubkey(k))
    return k, K_bytes


def _blind_and_sign(secret: bytes, k: int) -> tuple[bytes, bytes]:
    """Return (B_prime_bytes, C_prime_bytes)."""
    B_prime_bytes, _ = blind(secret)
    C_prime_bytes = sign_blinded(B_prime_bytes, k)
    return B_prime_bytes, C_prime_bytes


# ---------------------------------------------------------------------------
# DLEQ generation
# ---------------------------------------------------------------------------


class TestGenerateDLEQProof:
    def test_returns_e_and_s_fields(self) -> None:
        k, _ = _fresh_keypair()
        B, C = _blind_and_sign(b"secret", k)
        proof = generate_dleq_proof(B, C, k)
        assert "e" in proof and "s" in proof

    def test_e_is_64_char_hex(self) -> None:
        k, _ = _fresh_keypair()
        B, C = _blind_and_sign(b"secret", k)
        proof = generate_dleq_proof(B, C, k)
        assert len(proof["e"]) == 64
        bytes.fromhex(proof["e"])  # must be valid hex

    def test_s_is_64_char_hex(self) -> None:
        k, _ = _fresh_keypair()
        B, C = _blind_and_sign(b"secret", k)
        proof = generate_dleq_proof(B, C, k)
        assert len(proof["s"]) == 64
        bytes.fromhex(proof["s"])  # must be valid hex

    def test_two_proofs_for_same_inputs_differ(self) -> None:
        """DLEQ uses a fresh random nonce each call → outputs differ."""
        k, _ = _fresh_keypair()
        B, C = _blind_and_sign(b"nonce_test", k)
        p1 = generate_dleq_proof(B, C, k)
        p2 = generate_dleq_proof(B, C, k)
        # Extremely unlikely to collide (2^256 space)
        assert p1["e"] != p2["e"] or p1["s"] != p2["s"]


# ---------------------------------------------------------------------------
# DLEQ verification — valid cases
# ---------------------------------------------------------------------------


class TestVerifyDLEQProofValid:
    def test_basic_valid_proof(self) -> None:
        k, K_bytes = _fresh_keypair()
        B, C = _blind_and_sign(b"verify_basic", k)
        proof = generate_dleq_proof(B, C, k)
        assert verify_dleq_proof(B, C, K_bytes, proof["e"], proof["s"]) is True

    def test_multiple_secrets(self) -> None:
        k, K_bytes = _fresh_keypair()
        for i in range(5):
            B, C = _blind_and_sign(f"secret_{i}".encode(), k)
            proof = generate_dleq_proof(B, C, k)
            assert verify_dleq_proof(B, C, K_bytes, proof["e"], proof["s"]) is True, (
                f"Failed for secret index {i}"
            )

    def test_deterministic_with_same_r_and_k(self) -> None:
        """Deterministic test: same inputs always verify."""
        k = 0x1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF
        from cashu_mint.crypto.ec import N
        k = k % N or 1
        K_bytes = point_to_bytes(privkey_to_pubkey(k))

        B, C = _blind_and_sign(b"deterministic", k)
        proof = generate_dleq_proof(B, C, k)
        assert verify_dleq_proof(B, C, K_bytes, proof["e"], proof["s"]) is True


# ---------------------------------------------------------------------------
# DLEQ verification — rejection cases
# ---------------------------------------------------------------------------


class TestVerifyDLEQProofRejects:
    def setup_method(self) -> None:
        self.k, self.K_bytes = _fresh_keypair()
        self.B, self.C = _blind_and_sign(b"tamper_test", self.k)
        self.proof = generate_dleq_proof(self.B, self.C, self.k)

    def test_wrong_public_key(self) -> None:
        k2, K2_bytes = _fresh_keypair()
        assert verify_dleq_proof(
            self.B, self.C, K2_bytes, self.proof["e"], self.proof["s"]
        ) is False

    def test_tampered_C_prime(self) -> None:
        bad_C = self.C[:-1] + bytes([self.C[-1] ^ 0xFF])
        assert verify_dleq_proof(
            self.B, bad_C, self.K_bytes, self.proof["e"], self.proof["s"]
        ) is False

    def test_tampered_B_prime(self) -> None:
        bad_B = self.B[:-1] + bytes([self.B[-1] ^ 0xFF])
        assert verify_dleq_proof(
            bad_B, self.C, self.K_bytes, self.proof["e"], self.proof["s"]
        ) is False

    def test_tampered_e(self) -> None:
        e_bytes = bytes.fromhex(self.proof["e"])
        bad_e = (bytes([e_bytes[0] ^ 0x01]) + e_bytes[1:]).hex()
        assert verify_dleq_proof(
            self.B, self.C, self.K_bytes, bad_e, self.proof["s"]
        ) is False

    def test_tampered_s(self) -> None:
        s_bytes = bytes.fromhex(self.proof["s"])
        bad_s = (bytes([s_bytes[0] ^ 0x01]) + s_bytes[1:]).hex()
        assert verify_dleq_proof(
            self.B, self.C, self.K_bytes, self.proof["e"], bad_s
        ) is False

    def test_invalid_hex_returns_false(self) -> None:
        assert verify_dleq_proof(
            self.B, self.C, self.K_bytes, "not_hex", self.proof["s"]
        ) is False

    def test_wrong_key_used_for_signing(self) -> None:
        """C' signed with k1, but K_bytes is k2's pubkey → reject."""
        k2, K2_bytes = _fresh_keypair()
        B2, C2 = _blind_and_sign(b"mismatch", k2)
        proof2 = generate_dleq_proof(B2, C2, k2)
        # Present proof2 but with self.K_bytes (k1's key)
        assert verify_dleq_proof(
            B2, C2, self.K_bytes, proof2["e"], proof2["s"]
        ) is False


# ---------------------------------------------------------------------------
# sign_blinded_with_dleq integration
# ---------------------------------------------------------------------------


class TestSignBlindedWithDLEQ:
    def test_returns_C_prime_and_proof(self) -> None:
        k, K_bytes = _fresh_keypair()
        B, _ = blind(b"integration_test")
        C_prime, proof = sign_blinded_with_dleq(B, k)
        assert len(C_prime) == 33
        assert "e" in proof and "s" in proof

    def test_proof_is_valid(self) -> None:
        k, K_bytes = _fresh_keypair()
        B, _ = blind(b"valid_proof_test")
        C_prime, proof = sign_blinded_with_dleq(B, k)
        assert verify_dleq_proof(B, C_prime, K_bytes, proof["e"], proof["s"]) is True

    def test_C_prime_matches_sign_blinded(self) -> None:
        """C' from sign_blinded_with_dleq must equal plain sign_blinded."""
        k, _ = _fresh_keypair()
        B, r = blind(b"consistency_test")
        C_direct = sign_blinded(B, k)
        C_with_dleq, _ = sign_blinded_with_dleq(B, k)
        assert C_direct == C_with_dleq


# ---------------------------------------------------------------------------
# /v1/info advertises NUT-12
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_endpoint_lists_nut12() -> None:
    from httpx import ASGITransport, AsyncClient
    from cashu_mint.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/info")

    assert resp.status_code == 200
    data = resp.json()
    assert "nuts" in data
    assert "12" in data["nuts"], "NUT-12 must be listed in /v1/info nuts map"
    assert data["nuts"]["12"]["disabled"] is False


@pytest.mark.asyncio
async def test_info_endpoint_structure() -> None:
    from httpx import ASGITransport, AsyncClient
    from cashu_mint.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/info")

    assert resp.status_code == 200
    data = resp.json()
    for field in ("name", "version", "description", "nuts"):
        assert field in data, f"Missing field: {field}"
