---
id: 23
title: "Implement admin and monitoring (health, metrics, keyset rotation)"
priority: P2
severity: low
status: completed
source: feature_audit
file: "cashu_mint/nuts/admin.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: parallel
context_group: infrastructure
group_reason: "Admin/monitoring is independent of protocol implementation — parallel with other P2 tasks"
---

# Implement admin and monitoring (health, metrics, keyset rotation)

**Priority:** P2 (low)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/admin.py

## Problem

No admin or monitoring interface. Production mints need balance tracking, fee revenue reporting, keyset rotation tools, and health checks.

Without monitoring:
- Operators cannot detect Lightning node connectivity issues
- Fee revenue cannot be tracked
- Keyset rotation requires manual database manipulation
- There is no operational visibility into the mint's state

## How to Fix

Implement a minimal monitoring and admin layer:

```python
# cashu_mint/nuts/admin.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from cashu_mint.db.database import get_db
from cashu_mint.db.models import MintQuote, MeltQuote, Proof, Keyset

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check — returns 200 if server is running."""
    return {"status": "ok", "version": "0.1.0"}

@router.get("/metrics")  # Prometheus-compatible text format
async def metrics(db: Session = Depends(get_db)):
    """Export key mint metrics in Prometheus text format."""
    total_minted = db.query(MintQuote).filter(MintQuote.state == "ISSUED").count()
    total_melted = db.query(MeltQuote).filter(MeltQuote.state == "PAID").count()
    total_proofs = db.query(Proof).count()
    active_keysets = db.query(Keyset).filter(Keyset.active == True).count()

    return "\n".join([
        "# HELP cashu_mint_total_minted Total number of mint operations",
        f"cashu_mint_total_minted {total_minted}",
        "# HELP cashu_mint_total_melted Total number of melt operations",
        f"cashu_mint_total_melted {total_melted}",
        "# HELP cashu_mint_spent_proofs Total spent proofs in database",
        f"cashu_mint_spent_proofs {total_proofs}",
        "# HELP cashu_mint_active_keysets Number of active keysets",
        f"cashu_mint_active_keysets {active_keysets}",
    ])
```

Also implement a CLI management tool:
```python
# cashu_mint/cli.py
import typer

app = typer.Typer()

@app.command()
def rotate_keyset():
    """Generate a new active keyset and deactivate the current one."""
    ...

@app.command()
def show_balance():
    """Show total minted vs melted amounts."""
    ...
```

Steps:
1. Implement GET /health with Lightning connectivity check
2. Implement GET /metrics with Prometheus-format metrics
3. Implement simple CLI with typer for keyset rotation and balance display
4. Add balance tracking: track total_minted and total_melted amounts
5. Add keyset rotation: generate new keyset, mark old as inactive

## Acceptance Criteria

- [ ] GET /health returns 200 when server is healthy
- [ ] GET /metrics returns Prometheus-format metrics
- [ ] CLI `cashu-mint rotate-keyset` generates a new keyset
- [ ] CLI `cashu-mint balance` shows minted/melted totals
- [ ] Unhealthy Lightning backend reflected in health check response

## Notes

_Generated from feature_audit finding: Admin & Monitoring (low, effort: medium)._
