"""CLI management tool for cashu-mint operators.

Usage::

    python -m cashu_mint.cli --help
    python -m cashu_mint.cli rotate-keyset
    python -m cashu_mint.cli balance
    python -m cashu_mint.cli start

Requires the DATABASE_URL env var (or .env file) to be set correctly.
"""

import asyncio
import sys

import click

from cashu_mint.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_db_session():
    from cashu_mint.db.base import AsyncSessionLocal
    # Ensure models are registered with metadata
    import cashu_mint.db.keyset_models  # noqa: F401
    import cashu_mint.db.models  # noqa: F401
    return AsyncSessionLocal()


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Cashu Mint operator CLI."""


@cli.command("start")
@click.option("--host", default=settings.host, show_default=True, help="Bind host")
@click.option("--port", default=settings.port, show_default=True, help="Bind port")
@click.option("--reload", is_flag=True, default=False, help="Auto-reload on code changes")
def start_server(host: str, port: int, reload: bool) -> None:
    """Start the Cashu Mint HTTP server."""
    import uvicorn

    uvicorn.run("cashu_mint.main:app", host=host, port=port, reload=reload)


@cli.command("rotate-keyset")
@click.option(
    "--unit", default="sat", show_default=True, help="Currency unit for new keyset"
)
@click.option(
    "--fee-ppk", default=0, show_default=True, help="Input fee in parts-per-thousand"
)
def rotate_keyset(unit: str, fee_ppk: int) -> None:
    """Generate a new active keyset and deactivate the current one."""

    async def _run() -> None:
        from cashu_mint.db.base import create_all_tables
        from cashu_mint.db.keyset_crud import deactivate_keyset, get_active_keysets, save_keyset
        from cashu_mint.nuts.keyset import generate_keyset, master_key_from_hex, generate_master_key

        await create_all_tables()
        async with await _get_db_session() as db:
            # Resolve master key
            if settings.mint_private_key:
                master = master_key_from_hex(settings.mint_private_key)
            else:
                master = generate_master_key()
                click.echo(
                    f"WARNING: MINT_PRIVATE_KEY not set — using random key {master.hex()}",
                    err=True,
                )

            # Deactivate all current active keysets
            active = await get_active_keysets(db)
            for ks in active:
                await deactivate_keyset(db, ks.id)
                click.echo(f"Deactivated keyset: {ks.id}")

            # Generate and persist new keyset
            keyset_data = generate_keyset(master, unit=unit, input_fee_ppk=fee_ppk)
            await save_keyset(db, keyset_data)
            click.echo(f"Created new keyset:  {keyset_data['id']} (unit={unit}, fee_ppk={fee_ppk})")

    asyncio.run(_run())


@cli.command("balance")
def show_balance() -> None:
    """Show total minted vs melted amounts and current status."""

    async def _run() -> None:
        from cashu_mint.db.base import create_all_tables
        from cashu_mint.db.crud import (
            count_melt_quotes_by_state,
            count_mint_quotes_by_state,
            count_spent_proofs,
        )
        from cashu_mint.db.keyset_crud import get_active_keysets, get_all_keysets

        await create_all_tables()
        async with await _get_db_session() as db:
            total_issued = await count_mint_quotes_by_state(db, "ISSUED")
            total_melted = await count_melt_quotes_by_state(db, "PAID")
            pending_melts = await count_melt_quotes_by_state(db, "PENDING")
            unpaid_mints = await count_mint_quotes_by_state(db, "UNPAID")
            spent = await count_spent_proofs(db)
            active_ks = await get_active_keysets(db)
            all_ks = await get_all_keysets(db)

        click.echo(f"Mint:            {settings.mint_name}")
        click.echo(f"Database:        {settings.database_url}")
        click.echo(f"Lightning:       {settings.lightning_backend}")
        click.echo("")
        click.echo(f"Mint quotes:     {total_issued} issued, {unpaid_mints} pending")
        click.echo(f"Melt quotes:     {total_melted} paid, {pending_melts} pending")
        click.echo(f"Spent proofs:    {spent}")
        click.echo(f"Keysets:         {len(active_ks)} active / {len(all_ks)} total")

    asyncio.run(_run())


@cli.command("keyset-list")
def list_keysets() -> None:
    """List all keysets with their status."""

    async def _run() -> None:
        from cashu_mint.db.base import create_all_tables
        from cashu_mint.db.keyset_crud import get_all_keysets

        await create_all_tables()
        async with await _get_db_session() as db:
            keysets = await get_all_keysets(db)

        if not keysets:
            click.echo("No keysets found.")
            return

        click.echo(f"{'ID':<20} {'Unit':<8} {'Active':<8} {'Fee PPK':<10} {'Created'}")
        click.echo("-" * 70)
        for ks in keysets:
            active_str = "YES" if ks.active else "no"
            click.echo(
                f"{ks.id:<20} {ks.unit:<8} {active_str:<8} {ks.input_fee_ppk:<10} {ks.created_at}"
            )

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
