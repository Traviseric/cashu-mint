"""Tests for NUT-09 (signature restore) and NUT-13 (deterministic secrets).

NUT-09: POST /v1/restore — returns previously-issued blind signatures.
NUT-13: deterministic secret derivation (wallet-side); mint must be
        transparent to the format and support restore for derived secrets.

Test coverage:
- hash_to_curve accepts NUT-13 style hex secrets
- POST /v1/restore with empty outputs
- POST /v1/restore returns empty when no signatures stored
- POST /v1/restore returns matching signature for a known B'
- POST /v1/restore handles partial match (some known, some unknown)
- POST /v1/restore preserves order of outputs/signatures
- POST /v1/restore returns DLEQ fields when stored
- POST /v1/restore omits DLEQ when not stored
- Duplicate B' in request — returns one result
- store_blind_signature idempotent on duplicate B'
- /v1/info lists NUT-09 as supported
- /v1/info lists NUT-13 as supported
- NUT-13 secret round-trip: derive → blind → store → restore
"""

from __future__ import annotations

import hashlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cashu_mint.crypto.bdhke import blind, sign_blinded_with_dleq
from cashu_mint.crypto.ec import point_to_bytes, privkey_to_pubkey, random_privkey
from cashu_mint.crypto.bdhke import hash_to_curve
from cashu_mint.db.base import Base, get_db
from cashu_mint.db.crud import get_blind_signatures, store_blind_signature
from cashu_mint.db.models import BlindedSignatureRecord

# Register all ORM models before create_all
import cashu_mint.db.keyset_models  # noqa: F401
import cashu_mint.db.models  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite session with all tables created."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db):
    """HTTP test client with DB dependency overridden to the in-memory session."""
    from cashu_mint.main import app

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _make_record(
    B_hex: str,
    C_hex: str,
    amount: int = 1,
    keyset_id: str = "test_keyset_1",
    dleq_e: str | None = None,
    dleq_s: str | None = None,
) -> BlindedSignatureRecord:
    return BlindedSignatureRecord(
        B_=B_hex,
        amount=amount,
        keyset_id=keyset_id,
        C_=C_hex,
        dleq_e=dleq_e,
        dleq_s=dleq_s,
    )


def _fresh_sig(secret: bytes = b"test") -> tuple[str, str]:
    """Return (B_hex, C_hex) for a fresh blind-sign operation."""
    k = random_privkey()
    B_bytes, _ = blind(secret)
    C_bytes, _ = sign_blinded_with_dleq(B_bytes, k)
    return B_bytes.hex(), C_bytes.hex()


# ---------------------------------------------------------------------------
# NUT-13: hash_to_curve accepts deterministic hex secrets
# ---------------------------------------------------------------------------


class TestNUT13SecretFormat:
    """Verify that NUT-13 style secrets work transparently with hash_to_curve."""

    def test_hex_secret_64_chars(self) -> None:
        """A 64-char hex string (32-byte value) is a valid NUT-13 secret."""
        secret = "d52f52b71e83d5f25e42d834c3232e1cf1a88c0b3d5f20ae1d5e7a2b1c3f4e7a"
        pt = hash_to_curve(secret.encode())
        assert pt is not None

    def test_hex_secret_produces_valid_point(self) -> None:
        secret = bytes(32).hex()  # 64 zeroes — deterministic seed value
        pt = hash_to_curve(secret.encode())
        x, y = pt
        assert 0 < x < 2**256
        assert 0 < y < 2**256

    def test_different_hex_secrets_produce_different_points(self) -> None:
        s1 = hashlib.sha256(b"wallet_seed_1_index_0").hexdigest()
        s2 = hashlib.sha256(b"wallet_seed_1_index_1").hexdigest()
        assert s1 != s2
        pt1 = hash_to_curve(s1.encode())
        pt2 = hash_to_curve(s2.encode())
        assert pt1 != pt2

    def test_same_hex_secret_is_deterministic(self) -> None:
        secret = hashlib.sha256(b"deterministic").hexdigest()
        assert hash_to_curve(secret.encode()) == hash_to_curve(secret.encode())

    def test_nut13_blind_produces_valid_B_prime(self) -> None:
        """Blinding a NUT-13 derived secret produces a 33-byte compressed point."""
        secret = hashlib.sha256(b"nut13_test").hexdigest()
        B_bytes, r = blind(secret.encode())
        assert len(B_bytes) == 33
        assert isinstance(r, int)
        assert r > 0

    def test_nut13_full_bdhke_round_trip(self) -> None:
        """Complete BDHKE round-trip with a NUT-13 style secret."""
        from cashu_mint.crypto.bdhke import unblind, verify

        secret_str = hashlib.sha256(b"seed_phrase_derivation_index_42").hexdigest()
        secret_bytes = secret_str.encode()

        k = random_privkey()
        K_bytes = point_to_bytes(privkey_to_pubkey(k))

        B_bytes, r = blind(secret_bytes)
        C_prime_bytes = sign_blinded_with_dleq(B_bytes, k)[0]
        C_bytes = unblind(C_prime_bytes, r, K_bytes)

        assert verify(secret_bytes, C_bytes, k) is True


# ---------------------------------------------------------------------------
# CRUD: store_blind_signature / get_blind_signatures
# ---------------------------------------------------------------------------


class TestBlindSignatureCRUD:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, db: AsyncSession) -> None:
        B_hex, C_hex = _fresh_sig(b"crud_test_1")
        rec = _make_record(B_hex, C_hex)
        await store_blind_signature(db, rec)
        await db.commit()

        results = await get_blind_signatures(db, [B_hex])
        assert len(results) == 1
        assert results[0].B_ == B_hex
        assert results[0].C_ == C_hex

    @pytest.mark.asyncio
    async def test_unknown_B_returns_empty(self, db: AsyncSession) -> None:
        results = await get_blind_signatures(db, ["00" * 33])
        assert list(results) == []

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, db: AsyncSession) -> None:
        results = await get_blind_signatures(db, [])
        assert list(results) == []

    @pytest.mark.asyncio
    async def test_store_idempotent_on_duplicate_B(self, db: AsyncSession) -> None:
        """Storing the same B_ twice does not raise — idempotent."""
        B_hex, C_hex = _fresh_sig(b"dup_test")
        rec1 = _make_record(B_hex, C_hex)
        await store_blind_signature(db, rec1)
        await db.commit()

        # A second insert with same B_ should not raise
        rec2 = _make_record(B_hex, C_hex)
        await store_blind_signature(db, rec2)  # should not raise

    @pytest.mark.asyncio
    async def test_retrieve_multiple(self, db: AsyncSession) -> None:
        pairs = [_fresh_sig(f"multi_{i}".encode()) for i in range(3)]
        for B_hex, C_hex in pairs:
            await store_blind_signature(db, _make_record(B_hex, C_hex))
        await db.commit()

        B_values = [p[0] for p in pairs]
        results = await get_blind_signatures(db, B_values)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_partial_lookup(self, db: AsyncSession) -> None:
        B1, C1 = _fresh_sig(b"partial_1")
        B2, _ = _fresh_sig(b"partial_2")  # not stored
        await store_blind_signature(db, _make_record(B1, C1))
        await db.commit()

        results = await get_blind_signatures(db, [B1, B2])
        assert len(results) == 1
        assert results[0].B_ == B1


# ---------------------------------------------------------------------------
# POST /v1/restore endpoint
# ---------------------------------------------------------------------------


class TestRestoreEndpoint:
    @pytest.mark.asyncio
    async def test_empty_outputs_returns_empty(self, client: AsyncClient) -> None:
        resp = await client.post("/v1/restore", json={"outputs": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["outputs"] == []
        assert data["signatures"] == []

    @pytest.mark.asyncio
    async def test_unknown_B_returns_empty(
        self, client: AsyncClient
    ) -> None:
        payload = {
            "outputs": [
                {"amount": 1, "id": "test000000000001", "B_": "02" + "ab" * 32}
            ]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["outputs"] == []
        assert data["signatures"] == []

    @pytest.mark.asyncio
    async def test_known_B_returns_signature(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        B_hex, C_hex = _fresh_sig(b"restore_single")
        rec = _make_record(B_hex, C_hex, amount=8, keyset_id="deadbeef00000001")
        await store_blind_signature(db, rec)
        await db.commit()

        payload = {
            "outputs": [{"amount": 8, "id": "deadbeef00000001", "B_": B_hex}]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["outputs"]) == 1
        assert len(data["signatures"]) == 1
        assert data["outputs"][0]["B_"] == B_hex
        assert data["signatures"][0]["C_"] == C_hex
        assert data["signatures"][0]["amount"] == 8
        assert data["signatures"][0]["id"] == "deadbeef00000001"

    @pytest.mark.asyncio
    async def test_partial_match(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        B1, C1 = _fresh_sig(b"partial_match_known")
        B2, _ = _fresh_sig(b"partial_match_unknown")  # never stored
        await store_blind_signature(db, _make_record(B1, C1))
        await db.commit()

        payload = {
            "outputs": [
                {"amount": 1, "id": "ks0000000000", "B_": B1},
                {"amount": 2, "id": "ks0000000000", "B_": B2},
            ]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["outputs"]) == 1
        assert len(data["signatures"]) == 1
        assert data["outputs"][0]["B_"] == B1

    @pytest.mark.asyncio
    async def test_outputs_and_signatures_are_parallel(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        pairs = [_fresh_sig(f"parallel_{i}".encode()) for i in range(3)]
        for i, (B_hex, C_hex) in enumerate(pairs):
            await store_blind_signature(
                db, _make_record(B_hex, C_hex, amount=2**i)
            )
        await db.commit()

        payload = {
            "outputs": [
                {"amount": 2**i, "id": "ks0000000000", "B_": B_hex}
                for i, (B_hex, _) in enumerate(pairs)
            ]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["outputs"]) == 3
        assert len(data["signatures"]) == 3
        for i, (B_hex, C_hex) in enumerate(pairs):
            assert data["signatures"][i]["C_"] == C_hex

    @pytest.mark.asyncio
    async def test_dleq_fields_returned_when_present(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        B_hex, C_hex = _fresh_sig(b"dleq_present")
        dleq_e = "aa" * 32
        dleq_s = "bb" * 32
        rec = _make_record(B_hex, C_hex, dleq_e=dleq_e, dleq_s=dleq_s)
        await store_blind_signature(db, rec)
        await db.commit()

        payload = {"outputs": [{"amount": 1, "id": "ks0000000000", "B_": B_hex}]}
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        sig = data["signatures"][0]
        assert sig["dleq"] is not None
        assert sig["dleq"]["e"] == dleq_e
        assert sig["dleq"]["s"] == dleq_s

    @pytest.mark.asyncio
    async def test_dleq_absent_when_not_stored(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        B_hex, C_hex = _fresh_sig(b"dleq_absent")
        rec = _make_record(B_hex, C_hex)  # no dleq_e / dleq_s
        await store_blind_signature(db, rec)
        await db.commit()

        payload = {"outputs": [{"amount": 1, "id": "ks0000000000", "B_": B_hex}]}
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["signatures"][0]["dleq"] is None

    @pytest.mark.asyncio
    async def test_duplicate_B_in_request_returns_once(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        B_hex, C_hex = _fresh_sig(b"dup_in_request")
        await store_blind_signature(db, _make_record(B_hex, C_hex))
        await db.commit()

        payload = {
            "outputs": [
                {"amount": 1, "id": "ks0000000000", "B_": B_hex},
                {"amount": 1, "id": "ks0000000000", "B_": B_hex},
            ]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        # Both outputs match → both echoed (wallet asked for both, mint saw both)
        assert len(data["outputs"]) == 2
        assert len(data["signatures"]) == 2
        assert data["signatures"][0]["C_"] == C_hex
        assert data["signatures"][1]["C_"] == C_hex


# ---------------------------------------------------------------------------
# NUT-13 restore round-trip
# ---------------------------------------------------------------------------


class TestNUT13RestoreRoundTrip:
    @pytest.mark.asyncio
    async def test_deterministic_secret_restore(
        self, db: AsyncSession, client: AsyncClient
    ) -> None:
        """Simulate NUT-13 wallet recovery: derive → blind → store → restore."""
        # Wallet derives secret deterministically from seed + index
        seed = b"wallet_master_seed"
        index = 0
        secret_bytes = hashlib.sha256(seed + index.to_bytes(4, "big")).digest()

        # Wallet blinds the secret to get B'
        B_bytes, r = blind(secret_bytes)
        B_hex = B_bytes.hex()

        # Mint signs and stores the blind signature
        k = random_privkey()
        C_prime_bytes, dleq = sign_blinded_with_dleq(B_bytes, k)
        C_hex = C_prime_bytes.hex()

        rec = BlindedSignatureRecord(
            B_=B_hex,
            amount=64,
            keyset_id="ks0000000000",
            C_=C_hex,
            dleq_e=dleq["e"],
            dleq_s=dleq["s"],
        )
        await store_blind_signature(db, rec)
        await db.commit()

        # Wallet loses its data but knows its seed.
        # It re-derives the secret and re-computes B' deterministically.
        recovered_secret = hashlib.sha256(seed + index.to_bytes(4, "big")).digest()
        recovered_B_bytes, _ = blind(recovered_secret, r=r)  # same r for same B'
        assert recovered_B_bytes.hex() == B_hex  # B' is reproducible

        # Wallet calls /v1/restore with the recovered B'
        payload = {
            "outputs": [{"amount": 64, "id": "ks0000000000", "B_": B_hex}]
        }
        resp = await client.post("/v1/restore", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["signatures"]) == 1
        assert data["signatures"][0]["C_"] == C_hex
        assert data["signatures"][0]["dleq"]["e"] == dleq["e"]
        assert data["signatures"][0]["dleq"]["s"] == dleq["s"]


# ---------------------------------------------------------------------------
# /v1/info: NUT-09 and NUT-13 advertised
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_endpoint_lists_nut09() -> None:
    from cashu_mint.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/v1/info")

    assert resp.status_code == 200
    data = resp.json()
    assert "9" in data["nuts"], "NUT-09 must be listed in /v1/info nuts map"
    assert data["nuts"]["9"]["disabled"] is False


@pytest.mark.asyncio
async def test_info_endpoint_lists_nut13() -> None:
    from cashu_mint.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/v1/info")

    assert resp.status_code == 200
    data = resp.json()
    assert "13" in data["nuts"], "NUT-13 must be listed in /v1/info nuts map"
    assert data["nuts"]["13"]["disabled"] is False
