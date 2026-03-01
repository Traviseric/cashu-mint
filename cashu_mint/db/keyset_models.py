"""SQLAlchemy ORM models for keyset persistence (NUT-01/02).

These models define the ``keysets`` and ``keyset_keys`` database tables.
They register automatically with ``Base.metadata`` so that
``create_all_tables()`` picks them up.
"""

import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String

from cashu_mint.db.base import Base


class Keyset(Base):
    """Stores keyset metadata — one row per keyset."""

    __tablename__ = "keysets"

    id = Column(String(16), primary_key=True)  # hex keyset ID (16 chars = 8 bytes)
    unit = Column(String(10), nullable=False, default="sat")
    active = Column(Boolean, nullable=False, default=True)
    input_fee_ppk = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class KeysetKey(Base):
    """Stores one secp256k1 keypair per (keyset, denomination) pair.

    Only the private key is stored here.  The corresponding public key can
    be re-derived at any time via ``PrivateKey(bytes.fromhex(private_key)).public_key``.
    The private key is *never* returned via the API — only the public key is.
    """

    __tablename__ = "keyset_keys"

    keyset_id = Column(String(16), primary_key=True)
    amount = Column(BigInteger, primary_key=True)  # denomination in base unit
    private_key = Column(String(64), nullable=False)  # 32-byte key as 64-char hex
