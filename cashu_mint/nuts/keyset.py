"""NUT-01 and NUT-02: Keyset generation and ID derivation.

This module provides the cryptographic logic for keyset management:
- Deterministic keypair generation per denomination
- Keyset ID derivation per NUT-02 specification

Reference: https://github.com/cashubtc/nuts/blob/main/01.md
           https://github.com/cashubtc/nuts/blob/main/02.md
"""

import hashlib
import os
from typing import Optional

from coincurve import PrivateKey

# Standard Cashu denominations (powers of 2, in satoshis up to ~33 BTC).
# Each denomination gets its own secp256k1 keypair.
DENOMINATIONS: list[int] = [
    1, 2, 4, 8, 16, 32, 64, 128, 256, 512,
    1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288,
    1048576, 2097152, 4194304, 8388608, 16777216, 33554432,
]


def derive_keyset_id(keys: dict[int, bytes]) -> str:
    """Derive a keyset ID from compressed public keys per NUT-02.

    Algorithm:
        1. Sort entries by denomination amount (ascending).
        2. Concatenate all compressed public keys (33 bytes each).
        3. Compute SHA-256 of the concatenation.
        4. Prepend version byte 0x00.
        5. Return hex of (version_byte || first_7_bytes_of_hash).

    Args:
        keys: Mapping of denomination (int) → compressed public key (bytes).

    Returns:
        16-character hex string, e.g. ``"00a1b2c3d4e5f6a7"``.
    """
    sorted_pubkeys = b"".join(v for _, v in sorted(keys.items()))
    digest = hashlib.sha256(sorted_pubkeys).digest()
    return (b"\x00" + digest[:7]).hex()


def generate_keyset(
    master_key: bytes,
    unit: str = "sat",
    input_fee_ppk: int = 0,
) -> dict:
    """Generate a keyset with one secp256k1 keypair per denomination.

    Key derivation is deterministic: for denomination index ``i`` the child
    private key is ``SHA-256(master_key || i.to_bytes(4, 'big'))``.  The same
    ``master_key`` always produces the same keyset, enabling keyset recovery
    after a restart.

    Args:
        master_key:     32-byte master seed.
        unit:           Currency unit string (``"sat"``, ``"msat"``, etc.).
        input_fee_ppk:  Fee in parts-per-thousand (0 = no fee).

    Returns:
        A dict with fields::

            {
                "id":            str,   # hex keyset ID
                "unit":          str,
                "active":        bool,  # always True for freshly generated keysets
                "input_fee_ppk": int,
                "keys": {
                    <amount: int>: {
                        "private": str,  # 64-char hex (32-byte private key)
                        "public":  str,  # 66-char hex (33-byte compressed pubkey)
                    },
                    ...
                }
            }
    """
    keys: dict[int, dict] = {}
    pub_keys_bytes: dict[int, bytes] = {}

    for i, amount in enumerate(DENOMINATIONS):
        # Deterministic child key: SHA-256(master_key || index_4_bytes)
        child_secret = hashlib.sha256(master_key + i.to_bytes(4, "big")).digest()
        priv = PrivateKey(child_secret)
        pub_bytes = priv.public_key.format(compressed=True)
        keys[amount] = {
            "private": child_secret.hex(),
            "public": pub_bytes.hex(),
        }
        pub_keys_bytes[amount] = pub_bytes

    keyset_id = derive_keyset_id(pub_keys_bytes)
    return {
        "id": keyset_id,
        "unit": unit,
        "active": True,
        "input_fee_ppk": input_fee_ppk,
        "keys": keys,
    }


def generate_master_key() -> bytes:
    """Return a cryptographically random 32-byte master key."""
    return os.urandom(32)


def master_key_from_hex(hex_str: str) -> bytes:
    """Parse a hex-encoded master key string into bytes.

    Raises:
        ValueError: if the string is not valid 64-char hex.
    """
    key = bytes.fromhex(hex_str)
    if len(key) != 32:
        raise ValueError(
            f"Master key must be 32 bytes (64 hex chars), got {len(key)} bytes."
        )
    return key
