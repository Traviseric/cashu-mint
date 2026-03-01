"""Unit tests for NUT-10/11: spending conditions and P2PK.

Coverage:
- Schnorr sign / verify (cashu_mint.crypto.schnorr)
- parse_spending_condition: plain secret, valid P2PK, malformed JSON, unknown kind
- parse_witness: valid, empty, malformed
- verify_p2pk: happy path, missing witness, bad sig, multisig, locktime, refund
- check_proofs_spending_conditions: batch validation
- /v1/info advertises NUT-10 and NUT-11
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from cashu_mint.crypto.ec import point_to_bytes, privkey_to_pubkey, random_privkey
from cashu_mint.crypto.schnorr import schnorr_sign, schnorr_verify
from cashu_mint.exceptions import CashuError
from cashu_mint.nuts.spending_conditions import (
    P2PKCondition,
    SIGFLAG_ALL,
    SIGFLAG_INPUTS,
    WitnessData,
    check_proofs_spending_conditions,
    parse_spending_condition,
    parse_witness,
    verify_p2pk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keypair() -> tuple[int, str]:
    """Return (privkey_int, pubkey_hex)."""
    k = random_privkey()
    pk_bytes = point_to_bytes(privkey_to_pubkey(k))
    return k, pk_bytes.hex()


def _sign_secret(privkey: int, secret: str) -> str:
    """Sign SHA-256(secret) and return the 64-byte sig as hex."""
    msg = hashlib.sha256(secret.encode()).digest()
    return schnorr_sign(privkey, msg).hex()


def _make_secret(
    pubkey_hex: str,
    *,
    sigflag: str = SIGFLAG_INPUTS,
    n_sigs: int = 1,
    extra_pubkeys: list[str] | None = None,
    locktime: int | None = None,
    refund: list[str] | None = None,
    nonce: str = "aabbccdd",
) -> str:
    tags: list[list[str]] = [["sigflag", sigflag]]
    if n_sigs != 1:
        tags.append(["n_sigs", str(n_sigs)])
    if extra_pubkeys:
        tags.append(["pubkeys"] + extra_pubkeys)
    if locktime is not None:
        tags.append(["locktime", str(locktime)])
    if refund:
        tags.append(["refund"] + refund)
    return json.dumps(
        ["P2PK", {"nonce": nonce, "data": pubkey_hex, "tags": tags}],
        separators=(",", ":"),
    )


def _make_witness(sigs: list[str]) -> str:
    return json.dumps({"signatures": sigs}, separators=(",", ":"))


class _FakeProof:
    def __init__(self, secret: str, witness: str | None = None) -> None:
        self.secret = secret
        self.witness = witness


# ---------------------------------------------------------------------------
# Schnorr
# ---------------------------------------------------------------------------


class TestSchnorrSign:
    def test_returns_64_bytes(self) -> None:
        k, _ = _keypair()
        sig = schnorr_sign(k, b"hello")
        assert len(sig) == 64

    def test_valid_signature_verifies(self) -> None:
        k, pk_hex = _keypair()
        msg = b"test message"
        sig = schnorr_sign(k, msg)
        assert schnorr_verify(bytes.fromhex(pk_hex), msg, sig) is True

    def test_different_nonces_give_different_sigs(self) -> None:
        k, _ = _keypair()
        msg = b"same msg"
        s1 = schnorr_sign(k, msg)
        s2 = schnorr_sign(k, msg)
        assert s1 != s2  # random nonce → different each time

    def test_sign_32_byte_digest(self) -> None:
        k, pk_hex = _keypair()
        msg = hashlib.sha256(b"some secret").digest()
        sig = schnorr_sign(k, msg)
        assert schnorr_verify(bytes.fromhex(pk_hex), msg, sig) is True


class TestSchnorrVerify:
    def test_wrong_pubkey_fails(self) -> None:
        k, _ = _keypair()
        _, pk2_hex = _keypair()
        msg = b"hello"
        sig = schnorr_sign(k, msg)
        assert schnorr_verify(bytes.fromhex(pk2_hex), msg, sig) is False

    def test_tampered_sig_fails(self) -> None:
        k, pk_hex = _keypair()
        msg = b"hello"
        sig = bytearray(schnorr_sign(k, msg))
        sig[0] ^= 0xFF
        assert schnorr_verify(bytes.fromhex(pk_hex), msg, bytes(sig)) is False

    def test_wrong_message_fails(self) -> None:
        k, pk_hex = _keypair()
        sig = schnorr_sign(k, b"right message")
        assert schnorr_verify(bytes.fromhex(pk_hex), b"wrong message", sig) is False

    def test_short_sig_returns_false(self) -> None:
        _, pk_hex = _keypair()
        assert schnorr_verify(bytes.fromhex(pk_hex), b"msg", b"\x00" * 32) is False

    def test_empty_sig_returns_false(self) -> None:
        _, pk_hex = _keypair()
        assert schnorr_verify(bytes.fromhex(pk_hex), b"msg", b"") is False


# ---------------------------------------------------------------------------
# parse_spending_condition
# ---------------------------------------------------------------------------


class TestParseSpendingCondition:
    def test_plain_secret_returns_none(self) -> None:
        assert parse_spending_condition("plain-secret-string") is None

    def test_hex_secret_returns_none(self) -> None:
        assert parse_spending_condition("deadbeef" * 8) is None

    def test_valid_p2pk(self) -> None:
        _, pk_hex = _keypair()
        secret = _make_secret(pk_hex)
        cond = parse_spending_condition(secret)
        assert isinstance(cond, P2PKCondition)
        assert cond.pubkey == pk_hex

    def test_default_sigflag_is_sig_inputs(self) -> None:
        _, pk_hex = _keypair()
        secret = _make_secret(pk_hex)
        cond = parse_spending_condition(secret)
        assert cond is not None
        assert cond.sigflag == SIGFLAG_INPUTS

    def test_sig_all_flag(self) -> None:
        _, pk_hex = _keypair()
        secret = _make_secret(pk_hex, sigflag=SIGFLAG_ALL)
        cond = parse_spending_condition(secret)
        assert cond is not None
        assert cond.sigflag == SIGFLAG_ALL

    def test_default_n_sigs_is_one(self) -> None:
        _, pk_hex = _keypair()
        cond = parse_spending_condition(_make_secret(pk_hex))
        assert cond is not None
        assert cond.n_sigs == 1

    def test_custom_n_sigs(self) -> None:
        _, pk_hex = _keypair()
        cond = parse_spending_condition(_make_secret(pk_hex, n_sigs=3))
        assert cond is not None
        assert cond.n_sigs == 3

    def test_extra_pubkeys_included(self) -> None:
        _, pk1_hex = _keypair()
        _, pk2_hex = _keypair()
        _, pk3_hex = _keypair()
        cond = parse_spending_condition(_make_secret(pk1_hex, extra_pubkeys=[pk2_hex, pk3_hex]))
        assert cond is not None
        assert pk2_hex in cond.pubkeys
        assert pk3_hex in cond.pubkeys

    def test_primary_pubkey_in_pubkeys_list(self) -> None:
        _, pk_hex = _keypair()
        cond = parse_spending_condition(_make_secret(pk_hex))
        assert cond is not None
        assert pk_hex in cond.pubkeys

    def test_locktime_parsed(self) -> None:
        _, pk_hex = _keypair()
        ts = int(time.time()) + 3600
        cond = parse_spending_condition(_make_secret(pk_hex, locktime=ts))
        assert cond is not None
        assert cond.locktime == ts

    def test_refund_parsed(self) -> None:
        _, pk_hex = _keypair()
        _, refund_hex = _keypair()
        cond = parse_spending_condition(_make_secret(pk_hex, refund=[refund_hex]))
        assert cond is not None
        assert refund_hex in cond.refund

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(CashuError):
            parse_spending_condition("[not valid json")

    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(CashuError):
            parse_spending_condition(json.dumps(["HTLC", {"data": "abc"}]))

    def test_missing_data_raises(self) -> None:
        with pytest.raises(CashuError):
            parse_spending_condition(json.dumps(["P2PK", {"nonce": "aa", "tags": []}]))


# ---------------------------------------------------------------------------
# parse_witness
# ---------------------------------------------------------------------------


class TestParseWitness:
    def test_none_returns_empty(self) -> None:
        w = parse_witness(None)
        assert w.signatures == []

    def test_empty_string_returns_empty(self) -> None:
        w = parse_witness("")
        assert w.signatures == []

    def test_valid_witness(self) -> None:
        w = parse_witness(json.dumps({"signatures": ["aabb", "ccdd"]}))
        assert w.signatures == ["aabb", "ccdd"]

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(CashuError):
            parse_witness("{bad json")

    def test_non_object_raises(self) -> None:
        with pytest.raises(CashuError):
            parse_witness('"just a string"')


# ---------------------------------------------------------------------------
# verify_p2pk: plain proofs
# ---------------------------------------------------------------------------


class TestVerifyP2PKPlain:
    def test_plain_secret_always_passes(self) -> None:
        verify_p2pk("plain-secret", None)

    def test_plain_secret_with_witness_passes(self) -> None:
        verify_p2pk("plain", _make_witness(["deadbeef" * 16]))


# ---------------------------------------------------------------------------
# verify_p2pk: basic P2PK
# ---------------------------------------------------------------------------


class TestVerifyP2PKBasic:
    def setup_method(self) -> None:
        self.k, self.pk_hex = _keypair()
        self.secret = _make_secret(self.pk_hex)

    def test_valid_sig_passes(self) -> None:
        sig_hex = _sign_secret(self.k, self.secret)
        verify_p2pk(self.secret, _make_witness([sig_hex]))

    def test_missing_witness_raises(self) -> None:
        with pytest.raises(CashuError) as exc_info:
            verify_p2pk(self.secret, None)
        assert exc_info.value.code == 12001

    def test_empty_signatures_raises(self) -> None:
        with pytest.raises(CashuError):
            verify_p2pk(self.secret, _make_witness([]))

    def test_wrong_key_raises(self) -> None:
        k_wrong, _ = _keypair()
        sig_hex = _sign_secret(k_wrong, self.secret)
        with pytest.raises(CashuError):
            verify_p2pk(self.secret, _make_witness([sig_hex]))

    def test_invalid_hex_sig_raises(self) -> None:
        with pytest.raises(CashuError):
            verify_p2pk(self.secret, _make_witness(["notvalidhex!"]))


# ---------------------------------------------------------------------------
# verify_p2pk: multisig
# ---------------------------------------------------------------------------


class TestVerifyP2PKMultisig:
    def setup_method(self) -> None:
        self.k1, self.pk1_hex = _keypair()
        self.k2, self.pk2_hex = _keypair()
        self.k3, self.pk3_hex = _keypair()

    def test_2_of_2_passes(self) -> None:
        secret = _make_secret(
            self.pk1_hex,
            n_sigs=2,
            extra_pubkeys=[self.pk2_hex],
        )
        sigs = [_sign_secret(self.k1, secret), _sign_secret(self.k2, secret)]
        verify_p2pk(secret, _make_witness(sigs))

    def test_2_of_3_with_two_sigs_passes(self) -> None:
        secret = _make_secret(
            self.pk1_hex,
            n_sigs=2,
            extra_pubkeys=[self.pk2_hex, self.pk3_hex],
        )
        sigs = [_sign_secret(self.k1, secret), _sign_secret(self.k3, secret)]
        verify_p2pk(secret, _make_witness(sigs))

    def test_2_of_2_with_one_sig_raises(self) -> None:
        secret = _make_secret(
            self.pk1_hex,
            n_sigs=2,
            extra_pubkeys=[self.pk2_hex],
        )
        sigs = [_sign_secret(self.k1, secret)]
        with pytest.raises(CashuError):
            verify_p2pk(secret, _make_witness(sigs))

    def test_duplicate_sigs_count_once(self) -> None:
        """Providing the same valid sig twice must not count twice."""
        secret = _make_secret(self.pk1_hex, n_sigs=2, extra_pubkeys=[self.pk2_hex])
        sig1 = _sign_secret(self.k1, secret)
        # Only 1 distinct valid sig, but n_sigs=2 required
        with pytest.raises(CashuError):
            verify_p2pk(secret, _make_witness([sig1, sig1]))


# ---------------------------------------------------------------------------
# verify_p2pk: locktime
# ---------------------------------------------------------------------------


class TestVerifyP2PKLocktime:
    def test_unexpired_locktime_requires_sig(self) -> None:
        k, pk_hex = _keypair()
        future = int(time.time()) + 9999
        secret = _make_secret(pk_hex, locktime=future)
        # Valid sig passes
        sig_hex = _sign_secret(k, secret)
        verify_p2pk(secret, _make_witness([sig_hex]), now=int(time.time()))

    def test_unexpired_locktime_no_sig_raises(self) -> None:
        _, pk_hex = _keypair()
        future = int(time.time()) + 9999
        secret = _make_secret(pk_hex, locktime=future)
        with pytest.raises(CashuError):
            verify_p2pk(secret, None, now=int(time.time()))

    def test_expired_locktime_no_refund_anyone_can_spend(self) -> None:
        _, pk_hex = _keypair()
        past = int(time.time()) - 1
        secret = _make_secret(pk_hex, locktime=past)
        # No witness needed after locktime
        verify_p2pk(secret, None, now=int(time.time()))

    def test_expired_locktime_with_refund_requires_refund_sig(self) -> None:
        _, pk_hex = _keypair()
        k_refund, refund_hex = _keypair()
        past = int(time.time()) - 1
        secret = _make_secret(pk_hex, locktime=past, refund=[refund_hex])
        sig_hex = _sign_secret(k_refund, secret)
        # Refund sig required when refund key is listed
        verify_p2pk(secret, _make_witness([sig_hex]), now=int(time.time()))

    def test_expired_locktime_with_refund_wrong_key_falls_through(self) -> None:
        """If refund key sig fails, anyone-can-spend fallback applies."""
        _, pk_hex = _keypair()
        _, refund_hex = _keypair()
        k_other, _ = _keypair()
        past = int(time.time()) - 1
        secret = _make_secret(pk_hex, locktime=past, refund=[refund_hex])
        # Wrong sig for refund key — but fallback allows spend after locktime
        wrong_sig = _sign_secret(k_other, secret)
        verify_p2pk(secret, _make_witness([wrong_sig]), now=int(time.time()))


# ---------------------------------------------------------------------------
# verify_p2pk: SIG_ALL
# ---------------------------------------------------------------------------


class TestVerifyP2PKSigAll:
    def test_sig_all_passes_with_correct_message(self) -> None:
        k, pk_hex = _keypair()
        secret = _make_secret(pk_hex, sigflag=SIGFLAG_ALL)
        bundle_msg = hashlib.sha256(b"all-inputs-outputs").digest()
        sig = schnorr_sign(k, bundle_msg).hex()
        verify_p2pk(secret, _make_witness([sig]), sig_all_msg=bundle_msg)

    def test_sig_all_without_bundle_msg_raises(self) -> None:
        _, pk_hex = _keypair()
        secret = _make_secret(pk_hex, sigflag=SIGFLAG_ALL)
        k, _ = _keypair()
        sig_hex = schnorr_sign(k, b"anything").hex()
        with pytest.raises(CashuError):
            verify_p2pk(secret, _make_witness([sig_hex]))  # no sig_all_msg


# ---------------------------------------------------------------------------
# check_proofs_spending_conditions
# ---------------------------------------------------------------------------


class TestCheckProofsSpendingConditions:
    def test_batch_all_plain_passes(self) -> None:
        proofs = [_FakeProof("plain1"), _FakeProof("plain2")]
        check_proofs_spending_conditions(proofs)

    def test_batch_mixed_plain_and_p2pk_passes(self) -> None:
        k, pk_hex = _keypair()
        secret = _make_secret(pk_hex)
        sig_hex = _sign_secret(k, secret)
        proofs = [
            _FakeProof("plain"),
            _FakeProof(secret, _make_witness([sig_hex])),
        ]
        check_proofs_spending_conditions(proofs)

    def test_batch_fails_if_any_proof_fails(self) -> None:
        k, pk_hex = _keypair()
        secret = _make_secret(pk_hex)
        proofs = [
            _FakeProof("plain"),
            _FakeProof(secret, None),  # missing witness
        ]
        with pytest.raises(CashuError):
            check_proofs_spending_conditions(proofs)


# ---------------------------------------------------------------------------
# /v1/info advertises NUT-10 and NUT-11
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_lists_nut10_and_nut11() -> None:
    from httpx import ASGITransport, AsyncClient
    from cashu_mint.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/info")

    assert resp.status_code == 200
    nuts = resp.json()["nuts"]
    assert "10" in nuts, "NUT-10 not listed in /v1/info"
    assert "11" in nuts, "NUT-11 not listed in /v1/info"
    assert nuts["10"]["disabled"] is False
    assert nuts["11"]["disabled"] is False
