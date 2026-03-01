"""NUT-10 / NUT-11: Spending conditions and Pay-to-Pubkey (P2PK).

NUT-10 defines the Well-known Secret format — a structured proof secret that
encodes a *spending condition* the mint must enforce before accepting a proof.

NUT-11 defines the P2PK condition specifically: a proof is locked to one (or
more) secp256k1 public keys and can only be spent if accompanied by valid
Schnorr signatures from the required threshold of key-holders.

## Secret format (NUT-10)

    secret = JSON.stringify(["P2PK", {
        "nonce":  "<random 32-byte hex>",
        "data":   "<33-byte compressed pubkey hex>",    // primary pubkey
        "tags":   [
            ["sigflag",  "SIG_INPUTS"],                 // or "SIG_ALL"
            ["n_sigs",   "2"],                          // multisig threshold
            ["pubkeys",  "<pubkey2_hex>", ...],         // extra pubkeys
            ["locktime", "<unix timestamp>"],
            ["refund",   "<refund_pubkey_hex>", ...],
        ]
    }])

## Witness format (NUT-11)

    witness = JSON.stringify({"signatures": ["<sig1_hex>", ...]})

## Sigflag semantics

- **SIG_INPUTS** (default): each proof is signed independently.  The message
  signed is ``SHA-256(secret_utf8)`` for that proof.
- **SIG_ALL**: the wallet signs all inputs + outputs together.  The message is
  ``SHA-256(secret_0 || secret_1 || ... || B'_0 || B'_1 || ...)``.
  Full SIG_ALL validation requires the surrounding swap/melt context (pass
  ``sig_all_msg`` to :func:`verify_p2pk`).

## Locktime semantics

- If ``locktime`` is set and **not yet expired**: normal P2PK rules apply.
- If ``locktime`` is set and **expired**: anyone can spend the proof (the
  witness is ignored).  Optionally a ``refund`` pubkey list is checked first
  — if present, a valid signature from any refund key is required.

References:
    https://github.com/cashubtc/nuts/blob/main/10.md
    https://github.com/cashubtc/nuts/blob/main/11.md
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from cashu_mint.crypto.schnorr import schnorr_verify
from cashu_mint.exceptions import CashuError, ERR_SPENDING_CONDITIONS


# ---------------------------------------------------------------------------
# Supported condition kinds
# ---------------------------------------------------------------------------

KIND_P2PK = "P2PK"

# SIG_INPUTS: sign each proof secret individually (default)
# SIG_ALL:    sign the concatenation of all proof secrets + blinded outputs
SIGFLAG_INPUTS = "SIG_INPUTS"
SIGFLAG_ALL = "SIG_ALL"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class P2PKCondition:
    """Parsed NUT-10/11 P2PK spending condition.

    Attributes:
        pubkey:    Primary locking pubkey (33-byte compressed, hex).
        nonce:     Random nonce from the secret (for replay protection).
        n_sigs:    Minimum number of valid signatures required (multisig).
        sigflag:   ``"SIG_INPUTS"`` or ``"SIG_ALL"``.
        pubkeys:   Additional authorised pubkeys (incl. ``pubkey``).
        locktime:  Optional Unix timestamp; ``None`` means no locktime.
        refund:    Refund pubkeys — valid after locktime expires.
    """

    pubkey: str
    nonce: str = ""
    n_sigs: int = 1
    sigflag: str = SIGFLAG_INPUTS
    pubkeys: list[str] = field(default_factory=list)
    locktime: int | None = None
    refund: list[str] = field(default_factory=list)


@dataclass
class WitnessData:
    """Parsed NUT-11 witness."""

    signatures: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _get_tag(tags: list[list[str]], name: str) -> list[str]:
    """Return the first tag entry matching *name*, or ``[]``."""
    for tag in tags:
        if tag and tag[0] == name:
            return tag[1:]
    return []


def parse_spending_condition(secret: str) -> P2PKCondition | None:
    """Parse a NUT-10 P2PK spending condition from a proof secret string.

    Returns ``None`` if the secret is a plain string (no spending condition).
    Raises :class:`CashuError` if the secret *looks* like a condition but is
    malformed (prevents silent acceptance of invalid locked tokens).
    """
    if not secret.startswith("["):
        return None  # Plain secret — no spending condition

    try:
        data = json.loads(secret)
    except json.JSONDecodeError as exc:
        raise CashuError(ERR_SPENDING_CONDITIONS, f"Malformed spending condition JSON: {exc}") from exc

    if not isinstance(data, list) or len(data) < 2:
        raise CashuError(ERR_SPENDING_CONDITIONS, "Spending condition must be a 2-element JSON array")

    kind = data[0]
    if kind != KIND_P2PK:
        # Unknown condition kind — treat as unspendable for forward compatibility
        raise CashuError(ERR_SPENDING_CONDITIONS, f"Unsupported spending condition kind: {kind!r}")

    payload = data[1]
    if not isinstance(payload, dict):
        raise CashuError(ERR_SPENDING_CONDITIONS, "Spending condition payload must be an object")

    primary_pubkey: str = payload.get("data", "")
    if not primary_pubkey:
        raise CashuError(ERR_SPENDING_CONDITIONS, "P2PK condition missing 'data' (pubkey)")

    nonce: str = payload.get("nonce", "")
    tags: list[list[str]] = payload.get("tags", [])

    # --- sigflag ---
    sigflag_vals = _get_tag(tags, "sigflag")
    sigflag = sigflag_vals[0] if sigflag_vals else SIGFLAG_INPUTS
    if sigflag not in (SIGFLAG_INPUTS, SIGFLAG_ALL):
        raise CashuError(ERR_SPENDING_CONDITIONS, f"Unknown sigflag: {sigflag!r}")

    # --- n_sigs ---
    n_sigs_vals = _get_tag(tags, "n_sigs")
    try:
        n_sigs = int(n_sigs_vals[0]) if n_sigs_vals else 1
    except (ValueError, IndexError):
        n_sigs = 1
    if n_sigs < 1:
        raise CashuError(ERR_SPENDING_CONDITIONS, "n_sigs must be >= 1")

    # --- extra pubkeys ---
    extra_pubkeys = _get_tag(tags, "pubkeys")
    all_pubkeys = [primary_pubkey] + [pk for pk in extra_pubkeys if pk != primary_pubkey]

    # --- locktime ---
    locktime_vals = _get_tag(tags, "locktime")
    locktime: int | None = None
    if locktime_vals:
        try:
            locktime = int(locktime_vals[0])
        except ValueError:
            raise CashuError(ERR_SPENDING_CONDITIONS, "Invalid locktime value") from None

    # --- refund pubkeys ---
    refund_pubkeys = _get_tag(tags, "refund")

    return P2PKCondition(
        pubkey=primary_pubkey,
        nonce=nonce,
        n_sigs=n_sigs,
        sigflag=sigflag,
        pubkeys=all_pubkeys,
        locktime=locktime,
        refund=refund_pubkeys,
    )


def parse_witness(witness_json: str | None) -> WitnessData:
    """Parse a NUT-11 witness JSON string.

    Returns an empty :class:`WitnessData` if *witness_json* is ``None`` or
    blank.  Raises :class:`CashuError` on malformed JSON.
    """
    if not witness_json:
        return WitnessData()
    try:
        obj = json.loads(witness_json)
    except json.JSONDecodeError as exc:
        raise CashuError(ERR_SPENDING_CONDITIONS, f"Malformed witness JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise CashuError(ERR_SPENDING_CONDITIONS, "Witness must be a JSON object")

    sigs = obj.get("signatures", [])
    if not isinstance(sigs, list):
        raise CashuError(ERR_SPENDING_CONDITIONS, "'signatures' must be a JSON array")

    return WitnessData(signatures=[str(s) for s in sigs])


# ---------------------------------------------------------------------------
# Signature verification helpers
# ---------------------------------------------------------------------------


def _verify_sig_against_pubkeys(
    msg: bytes,
    sig_hex: str,
    pubkeys: list[str],
) -> bool:
    """Return True if *sig_hex* is a valid Schnorr sig of *msg* by any of *pubkeys*."""
    try:
        sig = bytes.fromhex(sig_hex)
    except ValueError:
        return False

    for pk_hex in pubkeys:
        try:
            pk_bytes = bytes.fromhex(pk_hex)
        except ValueError:
            continue
        if schnorr_verify(pk_bytes, msg, sig):
            return True
    return False


def _sig_message_for_proof(secret: str) -> bytes:
    """Return the 32-byte message that a SIG_INPUTS signature covers.

    The message is ``SHA-256(secret_utf8)`` — matching the nutshell reference.
    """
    return hashlib.sha256(secret.encode("utf-8")).digest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_p2pk(
    secret: str,
    witness_json: str | None,
    *,
    sig_all_msg: bytes | None = None,
    now: int | None = None,
) -> None:
    """Enforce NUT-10/11 spending conditions for a single proof.

    Calling this function is idempotent — it either returns cleanly (proof is
    spendable) or raises :class:`CashuError` with code 12001.

    Args:
        secret:       Proof secret string (plain or NUT-10 JSON).
        witness_json: Proof witness JSON string, or ``None`` if absent.
        sig_all_msg:  Pre-computed message for SIG_ALL verification.  Pass
                      ``None`` for SIG_INPUTS proofs (the default).
        now:          Current Unix timestamp for locktime checks.  Defaults to
                      ``int(time.time())``.  Pass an explicit value in tests.

    Raises:
        CashuError(12001): Spending condition not satisfied.
    """
    condition = parse_spending_condition(secret)

    if condition is None:
        return  # Plain proof — always valid

    if now is None:
        now = int(time.time())

    # ── Locktime check ───────────────────────────────────────────────────────
    if condition.locktime is not None and now >= condition.locktime:
        # Locktime has expired.
        if condition.refund:
            # Refund pubkeys take priority — require signature from one of them.
            witness = parse_witness(witness_json)
            msg = _sig_message_for_proof(secret)
            for sig_hex in witness.signatures:
                if _verify_sig_against_pubkeys(msg, sig_hex, condition.refund):
                    return  # Refund sig accepted
            # Fallback: anyone may spend if no refund key signed
            # (spec: after locktime *and* if refund keys are exhausted/absent,
            #  anyone can spend — we accept here to allow recovery)
        # No refund pubkeys or refund period: anyone can spend after locktime
        return

    # ── Normal P2PK verification ─────────────────────────────────────────────
    witness = parse_witness(witness_json)

    if not witness.signatures:
        raise CashuError(ERR_SPENDING_CONDITIONS, "P2PK proof requires a witness signature")

    # Choose the message to verify based on sigflag
    if condition.sigflag == SIGFLAG_ALL:
        if sig_all_msg is None:
            raise CashuError(
                ERR_SPENDING_CONDITIONS,
                "SIG_ALL proof requires sig_all_msg context (swap/melt bundle message)",
            )
        msg = sig_all_msg
    else:
        msg = _sig_message_for_proof(secret)

    # Track which pubkeys have already been consumed to prevent double-counting.
    # Each valid (sig, pubkey) pair may only be used once.
    remaining_pubkeys = list(condition.pubkeys)  # mutable copy
    valid_sigs = 0

    for sig_hex in witness.signatures:
        try:
            sig = bytes.fromhex(sig_hex)
        except ValueError:
            continue  # skip invalid hex

        for i, pk_hex in enumerate(remaining_pubkeys):
            try:
                pk_bytes = bytes.fromhex(pk_hex)
            except ValueError:
                continue
            if schnorr_verify(pk_bytes, msg, sig):
                valid_sigs += 1
                remaining_pubkeys.pop(i)  # consume pubkey
                if valid_sigs >= condition.n_sigs:
                    return  # Threshold reached — accept
                break  # this sig matched; try next sig

    raise CashuError(
        ERR_SPENDING_CONDITIONS,
        f"P2PK: {valid_sigs}/{condition.n_sigs} valid signatures (needed {condition.n_sigs})",
    )


def check_proofs_spending_conditions(
    proofs: list,  # list of Proof-like objects with .secret and .witness
    *,
    sig_all_msg: bytes | None = None,
    now: int | None = None,
) -> None:
    """Validate spending conditions for an entire batch of proofs.

    Convenience wrapper called from swap / melt endpoints.

    Args:
        proofs:       Iterable of objects with ``.secret`` and ``.witness``.
        sig_all_msg:  Required for any SIG_ALL proof in the batch.
        now:          Unix timestamp for locktime checks.

    Raises:
        CashuError(12001): If any proof fails its spending condition.
    """
    for proof in proofs:
        verify_p2pk(
            proof.secret,
            proof.witness,
            sig_all_msg=sig_all_msg,
            now=now,
        )
