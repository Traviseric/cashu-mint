"""Unit tests for NUT-01/02 keyset generation and ID derivation.

These tests run without a database or server — they only test the
cryptographic keyset logic in ``cashu_mint.nuts.keyset``.
"""

import hashlib

import pytest

from cashu_mint.crypto.ec import point_to_bytes, privkey_from_bytes, privkey_to_pubkey
from cashu_mint.nuts.keyset import (
    DENOMINATIONS,
    derive_keyset_id,
    generate_keyset,
    master_key_from_hex,
)


SAMPLE_MASTER_KEY = bytes.fromhex(
    "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
)


class TestDenominations:
    def test_denominations_are_powers_of_two(self) -> None:
        for i, d in enumerate(DENOMINATIONS):
            assert d == 2**i, f"DENOMINATIONS[{i}] should be {2**i}, got {d}"

    def test_denominations_are_sorted_ascending(self) -> None:
        assert DENOMINATIONS == sorted(DENOMINATIONS)

    def test_denominations_are_positive(self) -> None:
        assert all(d > 0 for d in DENOMINATIONS)


class TestDeriveKeysetId:
    def test_deterministic(self) -> None:
        keys = {1: bytes(33), 2: bytes(33)}
        assert derive_keyset_id(keys) == derive_keyset_id(keys)

    def test_returns_16_char_hex(self) -> None:
        keys = {1: bytes(33), 2: bytes(33)}
        kid = derive_keyset_id(keys)
        assert len(kid) == 16
        int(kid, 16)  # must be valid hex

    def test_starts_with_version_byte_00(self) -> None:
        keys = {1: bytes(33), 2: bytes(33)}
        kid = derive_keyset_id(keys)
        assert kid.startswith("00"), f"Expected '00' prefix, got {kid[:2]!r}"

    def test_different_keys_give_different_ids(self) -> None:
        keys_a = {1: b"\x02" + bytes(32), 2: b"\x02" + bytes(32)}
        keys_b = {1: b"\x03" + bytes(32), 2: b"\x03" + bytes(32)}
        assert derive_keyset_id(keys_a) != derive_keyset_id(keys_b)

    def test_order_independence(self) -> None:
        """ID must depend on denomination order, not insertion order."""
        key_a = b"\x02" + b"\xaa" * 32
        key_b = b"\x02" + b"\xbb" * 32
        keys_forward = {1: key_a, 2: key_b}
        keys_reversed = {2: key_b, 1: key_a}
        assert derive_keyset_id(keys_forward) == derive_keyset_id(keys_reversed)


class TestGenerateKeyset:
    def setup_method(self) -> None:
        self.keyset = generate_keyset(SAMPLE_MASTER_KEY)

    def test_has_required_fields(self) -> None:
        for field in ("id", "unit", "active", "input_fee_ppk", "keys"):
            assert field in self.keyset, f"Missing field: {field}"

    def test_default_unit_is_sat(self) -> None:
        assert self.keyset["unit"] == "sat"

    def test_active_by_default(self) -> None:
        assert self.keyset["active"] is True

    def test_default_fee_is_zero(self) -> None:
        assert self.keyset["input_fee_ppk"] == 0

    def test_has_key_for_every_denomination(self) -> None:
        assert set(self.keyset["keys"].keys()) == set(DENOMINATIONS)

    def test_private_keys_are_32_bytes_hex(self) -> None:
        for amount, pair in self.keyset["keys"].items():
            assert len(pair["private"]) == 64, f"amount={amount}: private key length"
            bytes.fromhex(pair["private"])  # valid hex

    def test_public_keys_are_33_bytes_compressed_hex(self) -> None:
        for amount, pair in self.keyset["keys"].items():
            assert len(pair["public"]) == 66, f"amount={amount}: public key length"
            pub_bytes = bytes.fromhex(pair["public"])
            assert pub_bytes[0] in (0x02, 0x03), "Not a compressed secp256k1 pubkey"

    def test_public_key_matches_private_key(self) -> None:
        for amount, pair in self.keyset["keys"].items():
            k = privkey_from_bytes(bytes.fromhex(pair["private"]))
            expected_pub = point_to_bytes(privkey_to_pubkey(k)).hex()
            assert pair["public"] == expected_pub, f"amount={amount}: pubkey mismatch"

    def test_keyset_id_derived_from_public_keys(self) -> None:
        pub_keys_bytes = {
            amt: bytes.fromhex(pair["public"])
            for amt, pair in self.keyset["keys"].items()
        }
        expected_id = derive_keyset_id(pub_keys_bytes)
        assert self.keyset["id"] == expected_id

    def test_deterministic_with_same_master_key(self) -> None:
        keyset2 = generate_keyset(SAMPLE_MASTER_KEY)
        assert self.keyset["id"] == keyset2["id"]
        assert self.keyset["keys"] == keyset2["keys"]

    def test_different_master_keys_give_different_keysets(self) -> None:
        other_key = b"\xff" * 32
        keyset2 = generate_keyset(other_key)
        assert self.keyset["id"] != keyset2["id"]

    def test_custom_unit(self) -> None:
        ks = generate_keyset(SAMPLE_MASTER_KEY, unit="msat")
        assert ks["unit"] == "msat"

    def test_custom_fee(self) -> None:
        ks = generate_keyset(SAMPLE_MASTER_KEY, input_fee_ppk=100)
        assert ks["input_fee_ppk"] == 100


class TestMasterKeyFromHex:
    def test_valid_hex(self) -> None:
        key = master_key_from_hex("aa" * 32)
        assert key == b"\xaa" * 32

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError):
            master_key_from_hex("aa" * 16)  # 16 bytes, not 32

    def test_invalid_hex_raises(self) -> None:
        with pytest.raises(ValueError):
            master_key_from_hex("gg" * 32)  # not hex
