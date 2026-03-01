"""SQLAlchemy ORM models for proof/quote persistence (NUT-03..NUT-05).

Tables:
- proofs       — spent token tracking (double-spend prevention)
- mint_quotes  — pending/paid mint (deposit) requests
- melt_quotes  — pending/paid melt (withdrawal) requests
"""

import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text

from cashu_mint.db.base import Base


class Proof(Base):
    """One row per spent token.

    The primary key is ``Y`` — the compressed secp256k1 point derived from the
    token secret via hash-to-curve.  Using this as PK means a duplicate-key
    error (or SELECT-then-INSERT under SERIALIZABLE isolation) is the atomic
    double-spend check.
    """

    __tablename__ = "proofs"

    Y = Column(String(66), primary_key=True)  # compressed pubkey hex (33 bytes)
    amount = Column(BigInteger, nullable=False)
    keyset_id = Column(String(16), nullable=False)
    secret = Column(Text, nullable=False)
    C = Column(String(66), nullable=False)  # unblinded signature hex
    witness = Column(Text, nullable=True)  # NUT-10/11 spending condition witness
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class MintQuote(Base):
    """One row per mint (deposit) quote.

    Lifecycle:  UNPAID → PAID → ISSUED
                UNPAID → EXPIRED
    """

    __tablename__ = "mint_quotes"

    quote_id = Column(String(36), primary_key=True)  # UUID
    method = Column(String(10), nullable=False, default="bolt11")
    request = Column(Text, nullable=False)  # Lightning invoice (bolt11)
    unit = Column(String(10), nullable=False, default="sat")
    amount = Column(BigInteger, nullable=False)
    state = Column(String(10), nullable=False, default="UNPAID")
    expiry = Column(Integer, nullable=False)  # unix timestamp
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class MeltQuote(Base):
    """One row per melt (withdrawal) quote.

    Lifecycle:  UNPAID → PENDING → PAID
                UNPAID → EXPIRED
    """

    __tablename__ = "melt_quotes"

    quote_id = Column(String(36), primary_key=True)  # UUID
    method = Column(String(10), nullable=False, default="bolt11")
    request = Column(Text, nullable=False)  # Lightning invoice to pay
    unit = Column(String(10), nullable=False, default="sat")
    amount = Column(BigInteger, nullable=False)
    fee_reserve = Column(BigInteger, nullable=False)
    state = Column(String(10), nullable=False, default="UNPAID")
    payment_preimage = Column(String(64), nullable=True)
    change = Column(Text, nullable=True)  # JSON: BlindedSignatures for NUT-08 fee return
    expiry = Column(Integer, nullable=False)  # unix timestamp
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
