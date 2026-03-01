---
id: 12
title: "Implement operator configuration system (env vars + config file)"
priority: P1
severity: high
status: completed
source: feature_audit
file: "cashu_mint/config.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: infrastructure
group_reason: "Configuration is needed by all components — Lightning backend, database, keyset management, and info endpoint all read from config"
---

# Implement operator configuration system (env vars + config file)

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/config.py

## Problem

No configuration system exists. Mint operators need to configure Lightning backend credentials, database connection, fee rates, keyset settings, and rate limits.

Without configuration:
- Lightning backend credentials are hardcoded (security risk)
- Database URL is hardcoded (not deployable)
- Fee rates cannot be adjusted
- Mint identity (private key, name) cannot be set

## How to Fix

Implement `cashu_mint/config.py` using Pydantic Settings:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Mint identity
    MINT_PRIVATE_KEY: str = ""          # hex-encoded 32-byte key (required)
    MINT_NAME: str = "My Cashu Mint"
    MINT_DESCRIPTION: str = "A Cashu protocol mint"
    MINT_DESCRIPTION_LONG: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./cashu_mint.db"

    # Lightning backend
    LIGHTNING_BACKEND: str = "fake"     # fake | lnbits | lnd | cln
    LNBITS_ENDPOINT: str = ""
    LNBITS_API_KEY: str = ""
    LND_GRPC_HOST: str = ""
    LND_MACAROON: str = ""
    LND_TLS_CERT: str = ""

    # Mint limits
    MAX_ORDER: int = 64                 # max denomination exponent (2^64 sats)
    INPUT_FEE_PPK: int = 0             # input fee in parts-per-thousand
    MAX_MINT_AMOUNT: int = 100000      # max single mint amount in sats
    MAX_MELT_AMOUNT: int = 100000      # max single melt amount in sats

    # Quote settings
    MINT_QUOTE_TTL: int = 3600         # seconds
    MELT_QUOTE_TTL: int = 3600         # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

Steps:
1. Install `pydantic-settings` dependency
2. Create `cashu_mint/config.py` with `Settings` class
3. Create `.env.example` showing all available options
4. Add `.env` to `.gitignore`
5. Update all components to import from `config.py` instead of hardcoded values
6. Add startup validation: fail fast if `MINT_PRIVATE_KEY` is missing/invalid

## Acceptance Criteria

- [ ] All configurable values read from environment variables or `.env` file
- [ ] App fails to start with clear error message if MINT_PRIVATE_KEY not set
- [ ] `.env.example` documents all configuration options with descriptions
- [ ] `.env` excluded from version control
- [ ] Lightning backend selection works via `LIGHTNING_BACKEND` env var
- [ ] Database URL configurable (SQLite default, PostgreSQL supported)

## Notes

_Generated from feature_audit finding: Operator Configuration System (medium)._
