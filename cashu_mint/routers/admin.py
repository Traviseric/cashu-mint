"""Admin and monitoring endpoints (health check + Prometheus metrics).

Routes:
    GET /v1/health   — liveness check
    GET /v1/metrics  — Prometheus-format operational metrics
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from cashu_mint.config import settings
from cashu_mint.db.base import get_db
from cashu_mint.db.crud import (
    count_melt_quotes_by_state,
    count_mint_quotes_by_state,
    count_spent_proofs,
)
from cashu_mint.db.keyset_crud import get_active_keysets

router = APIRouter(tags=["admin"])


@router.get(
    "/health",
    summary="Health check",
    responses={200: {"description": "Mint is healthy"}},
)
async def health_check() -> dict:
    """Return 200 if the mint server is running and reachable."""
    return {
        "status": "ok",
        "mint": settings.mint_name,
        "version": "0.1.0",
        "lightning_backend": settings.lightning_backend,
    }


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def metrics(db: AsyncSession = Depends(get_db)) -> str:
    """Export key mint metrics in Prometheus text exposition format."""
    issued = await count_mint_quotes_by_state(db, "ISSUED")
    paid_melts = await count_melt_quotes_by_state(db, "PAID")
    pending_melts = await count_melt_quotes_by_state(db, "PENDING")
    spent_proofs = await count_spent_proofs(db)
    active_ks = await get_active_keysets(db)

    lines = [
        "# HELP cashu_mint_total_issued Total mint (issue) operations completed",
        f"cashu_mint_total_issued {issued}",
        "# HELP cashu_mint_total_melted Total melt (redeem) operations completed",
        f"cashu_mint_total_melted {paid_melts}",
        "# HELP cashu_mint_pending_melts Melt operations currently pending payment",
        f"cashu_mint_pending_melts {pending_melts}",
        "# HELP cashu_mint_spent_proofs Total spent proofs stored (double-spend DB size)",
        f"cashu_mint_spent_proofs {spent_proofs}",
        "# HELP cashu_mint_active_keysets Number of active signing keysets",
        f"cashu_mint_active_keysets {len(active_ks)}",
    ]
    return "\n".join(lines) + "\n"
