"""Alembic environment configuration.

Uses a lightweight sync SQLAlchemy setup for migrations (separate from the
async engine used at runtime).  DATABASE_URL is read from the environment,
with the async driver prefix stripped for sync compatibility.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import DeclarativeBase

from alembic import context

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Build a sync database URL from the environment or alembic.ini
# ---------------------------------------------------------------------------
_raw_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")
# Strip async driver prefixes so we get a plain sync connection for migrations
_sync_url = (
    _raw_url
    .replace("sqlite+aiosqlite://", "sqlite://")
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("mysql+aiomysql://", "mysql://")
)
if not _sync_url:
    _sync_url = "sqlite:///./cashu_mint.db"

config.set_main_option("sqlalchemy.url", _sync_url)

# ---------------------------------------------------------------------------
# Import all ORM models so they register with a fresh metadata
# We create a minimal Base here to avoid the async engine creation in base.py
# ---------------------------------------------------------------------------


class _MigrationBase(DeclarativeBase):
    """Standalone Base used only for migration autogenerate.

    Models declare their tables via __tablename__ and Column definitions;
    all we need here is for the metadata to be populated, which happens
    automatically when the model classes are defined.
    """


# Monkey-patch the module-level Base so imported models attach to _MigrationBase
import cashu_mint.db.base as _db_base  # noqa: E402

_original_base = _db_base.Base
_db_base.Base = _MigrationBase  # type: ignore[assignment]

# Now import the models — they will subclass _MigrationBase and populate metadata
import cashu_mint.db.keyset_models  # noqa: F401, E402
import cashu_mint.db.models  # noqa: F401, E402

# Restore original Base (not strictly necessary but clean)
_db_base.Base = _original_base  # type: ignore[assignment]

target_metadata = _MigrationBase.metadata


# ---------------------------------------------------------------------------
# Offline mode (generate SQL scripts without a live DB connection)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (run against a live sync DB connection)
# ---------------------------------------------------------------------------


def run_migrations_online() -> None:
    connectable = create_engine(_sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
