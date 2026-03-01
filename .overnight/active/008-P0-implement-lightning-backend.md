---
id: 8
title: "Implement Lightning backend integration (LND/CLN/LNbits)"
priority: P0
severity: critical
status: pending
source: feature_audit
file: "cashu_mint/lightning/"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: lightning_integration
group_reason: "Lightning backend is shared dependency for NUT-04 minting (create invoice) and NUT-05 melting (pay invoice)"
---

# Implement Lightning backend integration (LND/CLN/LNbits)

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/lightning/

## Problem

No Lightning backend integration exists. The mint cannot create invoices, check payment status, or pay Lightning invoices — all of which are required for NUT-04 and NUT-05.

Without Lightning integration:
- Users cannot deposit Bitcoin to receive ecash (NUT-04 broken)
- Users cannot redeem ecash for Bitcoin (NUT-05 broken)
- The mint is not usable as an ecash mint

The mint needs to communicate with a real Lightning node (LND, CLN, LNbits, or fake for testing).

## How to Fix

Implement a Lightning backend abstraction with a concrete LNbits implementation (simplest to get started):

```python
# cashu_mint/lightning/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Invoice:
    payment_request: str   # BOLT11 invoice string
    payment_hash: str
    amount_sat: int
    expiry: int

@dataclass
class PaymentResult:
    paid: bool
    preimage: str | None
    fee_sat: int

class LightningBackend(ABC):
    @abstractmethod
    async def create_invoice(self, amount_sat: int, memo: str = "") -> Invoice:
        """Create a Lightning invoice for the given amount."""
        ...

    @abstractmethod
    async def check_invoice(self, payment_hash: str) -> bool:
        """Return True if invoice has been paid."""
        ...

    @abstractmethod
    async def pay_invoice(self, payment_request: str, fee_limit_sat: int) -> PaymentResult:
        """Pay a Lightning invoice. Returns result with preimage."""
        ...

    @abstractmethod
    async def get_fee_estimate(self, payment_request: str) -> int:
        """Estimate fee in sats for paying this invoice."""
        ...
```

```python
# cashu_mint/lightning/lnbits.py
import httpx
from cashu_mint.lightning.base import LightningBackend, Invoice, PaymentResult

class LNbitsBackend(LightningBackend):
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.headers = {"X-Api-Key": api_key}

    async def create_invoice(self, amount_sat: int, memo: str = "") -> Invoice:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.url}/api/v1/payments",
                headers=self.headers,
                json={"out": False, "amount": amount_sat, "memo": memo}
            )
            resp.raise_for_status()
            data = resp.json()
        return Invoice(
            payment_request=data["payment_request"],
            payment_hash=data["payment_hash"],
            amount_sat=amount_sat,
            expiry=3600
        )

    async def check_invoice(self, payment_hash: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/api/v1/payments/{payment_hash}",
                headers=self.headers
            )
            resp.raise_for_status()
        return resp.json().get("paid", False)

    async def pay_invoice(self, payment_request: str, fee_limit_sat: int) -> PaymentResult:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.url}/api/v1/payments",
                headers=self.headers,
                json={"out": True, "bolt11": payment_request}
            )
            resp.raise_for_status()
            data = resp.json()
        return PaymentResult(
            paid=True,
            preimage=data.get("payment_hash"),
            fee_sat=0
        )

    async def get_fee_estimate(self, payment_request: str) -> int:
        return 2  # LNbits doesn't have a fee estimate endpoint; use conservative default
```

Also implement a `FakeBackend` for testing that auto-pays invoices.

Steps:
1. Create `cashu_mint/lightning/base.py` with abstract interface
2. Implement `LNbitsBackend` (easiest to test without a full node)
3. Implement `FakeBackend` that always returns paid=True (for testing)
4. Create factory function that selects backend based on `LIGHTNING_BACKEND` env var
5. Wire backend into app via dependency injection

## Acceptance Criteria

- [ ] Abstract `LightningBackend` interface defined with create/check/pay/estimate methods
- [ ] `LNbitsBackend` connects to LNbits instance and creates/pays invoices
- [ ] `FakeBackend` usable in tests (auto-pays invoices)
- [ ] Backend selected via `LIGHTNING_BACKEND` environment variable
- [ ] Connection errors are caught and re-raised as structured Cashu errors

## Notes

_Generated from feature_audit finding: Lightning Backend Integration (critical, blocking)._
