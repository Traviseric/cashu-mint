---
id: 21
title: "Implement NUT-23: BOLT11 payment method declaration in info/quotes"
priority: P2
severity: medium
status: pending
source: feature_audit
file: "cashu_mint/nuts/info.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: parallel
context_group: protocol_extensions
group_reason: "NUT-23 is an update to the info endpoint (task 11) and quote endpoint response format"
---

# Implement NUT-23: BOLT11 payment method declaration in info/quotes

**Priority:** P2 (medium)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/info.py

## Problem

NUT-23: No explicit BOLT11 payment method declaration. The mint must advertise supported payment methods in its info endpoint and quote responses.

Per NUT-23, the mint must explicitly declare BOLT11 as a payment method with unit support in its info endpoint. Quote responses should also include `method: "bolt11"` in their payloads.

## How to Fix

Update GET /v1/info response to include NUT-23 payment method declarations:

```python
# In MintInfoResponse, update nuts dict:
nuts = {
    "4": {
        "methods": [
            {
                "method": "bolt11",
                "unit": "sat",
                "min_amount": 1,
                "max_amount": settings.MAX_MINT_AMOUNT
            }
        ],
        "disabled": False
    },
    "5": {
        "methods": [
            {
                "method": "bolt11",
                "unit": "sat",
                "min_amount": 1,
                "max_amount": settings.MAX_MELT_AMOUNT
            }
        ],
        "disabled": False
    }
}
```

Also ensure all quote responses include `method: "bolt11"` and `unit: "sat"`:
```python
class MintQuoteResponse(BaseModel):
    quote: str
    request: str
    method: str = "bolt11"  # explicit per NUT-23
    unit: str
    state: str
    expiry: int
```

Steps:
1. Update GET /v1/info nuts field to include NUT-04/05 method declarations per NUT-23
2. Add `method` field to all quote request/response models
3. Include min/max amount bounds per payment method
4. Advertise NUT-23 support in GET /v1/info

## Acceptance Criteria

- [ ] GET /v1/info includes `method: bolt11` in NUT-04 and NUT-05 entries
- [ ] Min/max amount bounds declared for bolt11 method
- [ ] Quote responses include `method: "bolt11"` field
- [ ] NUT-23 listed in supported nuts

## Notes

_Generated from feature_audit finding: NUT-23 BOLT11 Payment Method (medium, effort: low)._
