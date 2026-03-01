---
id: 3
title: "Implement database persistence layer (keysets, proofs, quotes)"
priority: P0
severity: critical
status: completed
source: feature_audit
file: "cashu_mint/db/"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: infrastructure
group_reason: "Database layer is shared by keyset management, double-spend prevention, and mint/melt quote flows"
---

# Implement database persistence layer (keysets, proofs, quotes)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/db/

## Problem

No database layer exists. The mint has no persistence for keysets, spent proofs, mint/melt quotes, or pending operations. Without this, double-spend prevention is impossible.

Specifically missing:
- No database schema or migrations
- No ORM models for: keysets, proofs (spent tokens), mint_quotes, melt_quotes
- No connection pooling or session management
- No atomic operations (required for TOCTOU-safe double-spend prevention)

Without persistence, the mint cannot function at all — restarting the server would reset all state, and concurrent requests could cause double-spends.

## How to Fix

Implement SQLAlchemy models + Alembic migrations:

```python
# cashu_mint/db/models.py
from sqlalchemy import Column, String, Integer, Boolean, BigInteger, DateTime, Text
from sqlalchemy.orm import DeclarativeBase
import datetime

class Base(DeclarativeBase):
    pass

class Keyset(Base):
    __tablename__ = "keysets"
    id = Column(String(16), primary_key=True)  # hex-encoded keyset ID
    unit = Column(String(10), nullable=False, default="sat")
    active = Column(Boolean, default=True)
    input_fee_ppk = Column(Integer, default=0)  # fee in parts-per-thousand
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class KeysetKey(Base):
    __tablename__ = "keyset_keys"
    keyset_id = Column(String(16), primary_key=True)
    amount = Column(Integer, primary_key=True)  # denomination in sats
    private_key = Column(String(64), nullable=False)  # hex-encoded 32-byte key

class Proof(Base):
    __tablename__ = "proofs"
    Y = Column(String(66), primary_key=True)  # compressed pubkey hex (spent token ID)
    amount = Column(Integer, nullable=False)
    keyset_id = Column(String(16), nullable=False)
    secret = Column(Text, nullable=False)
    C = Column(String(66), nullable=False)  # signature hex
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MintQuote(Base):
    __tablename__ = "mint_quotes"
    quote_id = Column(String(36), primary_key=True)  # UUID
    method = Column(String(10), default="bolt11")
    request = Column(Text, nullable=False)  # Lightning invoice
    unit = Column(String(10), default="sat")
    amount = Column(Integer, nullable=False)
    state = Column(String(10), default="UNPAID")  # UNPAID/PAID/ISSUED/EXPIRED
    expiry = Column(Integer, nullable=False)  # unix timestamp
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MeltQuote(Base):
    __tablename__ = "melt_quotes"
    quote_id = Column(String(36), primary_key=True)  # UUID
    method = Column(String(10), default="bolt11")
    request = Column(Text, nullable=False)  # Lightning invoice to pay
    unit = Column(String(10), default="sat")
    amount = Column(Integer, nullable=False)
    fee_reserve = Column(Integer, nullable=False)
    state = Column(String(10), default="UNPAID")  # UNPAID/PENDING/PAID/EXPIRED
    payment_preimage = Column(String(64), nullable=True)
    expiry = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

Steps:
1. Create `cashu_mint/db/models.py` with SQLAlchemy models (above)
2. Create `cashu_mint/db/database.py` with engine setup and session factory
3. Initialize Alembic: `alembic init alembic`
4. Create initial migration covering all tables
5. Add `cashu_mint/db/crud.py` with repository functions
6. Ensure proof insertion uses `SELECT FOR UPDATE` or equivalent atomic check-and-insert for double-spend safety
7. Support both SQLite (development) and PostgreSQL (production) via `DATABASE_URL` env var

## Acceptance Criteria

- [ ] All 5 tables created by Alembic migration
- [ ] `alembic upgrade head` runs without errors on fresh database
- [ ] CRUD operations work for all models
- [ ] Proof insertion is atomic (concurrent inserts for same Y value: only one succeeds)
- [ ] SQLite works for development, PostgreSQL connection string accepted

## Notes

_Generated from feature_audit finding: Database / Persistence Layer (critical, blocking)._
