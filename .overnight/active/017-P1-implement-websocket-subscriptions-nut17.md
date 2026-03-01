---
id: 17
title: "Implement NUT-17: WebSocket subscriptions for real-time quote updates"
priority: P1
severity: high
status: pending
source: feature_audit
file: "cashu_mint/nuts/websocket.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: long_running
context_group: protocol_extensions
group_reason: "WebSocket subscriptions require deep integration with quote state changes across NUT-04 and NUT-05"
---

# Implement NUT-17: WebSocket subscriptions for real-time quote updates

**Priority:** P1 (high)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/nuts/websocket.py

## Problem

NUT-17: No WebSocket subscription support. Real-time quote status updates (mint/melt payment confirmations) require WebSocket subscriptions.

Without WebSocket support, wallets must poll GET /v1/mint/quote/{id} repeatedly to check if a Lightning payment was received. This is inefficient and creates latency between payment confirmation and token issuance.

With NUT-17, wallets subscribe to quote state changes and receive instant push notifications when a quote transitions from UNPAID → PAID, enabling near-instant token issuance after payment.

## How to Fix

Implement WebSocket endpoint per NUT-17 spec:

```python
# cashu_mint/nuts/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Any
import asyncio
import json

router = APIRouter()

# Connection manager for active subscriptions
class SubscriptionManager:
    def __init__(self):
        self.subscriptions: dict[str, list[WebSocket]] = {}

    async def subscribe(self, ws: WebSocket, kind: str, filters: list[str]):
        """Register a WebSocket for quote state change events."""
        for f in filters:
            key = f"{kind}:{f}"
            if key not in self.subscriptions:
                self.subscriptions[key] = []
            self.subscriptions[key].append(ws)

    async def notify(self, kind: str, filter_val: str, payload: dict):
        """Push event to all subscribers for this filter."""
        key = f"{kind}:{filter_val}"
        dead = []
        for ws in self.subscriptions.get(key, []):
            try:
                await ws.send_json({"jsonrpc": "2.0", "method": "subscribe",
                                     "params": {"kind": kind, "filters": [filter_val],
                                                "payload": payload}})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.subscriptions[key].remove(ws)

    def unsubscribe(self, ws: WebSocket):
        for key in list(self.subscriptions.keys()):
            self.subscriptions[key] = [w for w in self.subscriptions[key] if w != ws]

manager = SubscriptionManager()

@router.websocket("/v1/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            if data.get("method") == "subscribe":
                params = data.get("params", {})
                await manager.subscribe(ws, params["kind"], params["filters"])
                await ws.send_json({"jsonrpc": "2.0", "id": data.get("id"),
                                     "result": {"status": "OK", "subId": "sub1"}})
            elif data.get("method") == "unsubscribe":
                manager.unsubscribe(ws)
    except WebSocketDisconnect:
        manager.unsubscribe(ws)
```

Integrate notification calls into quote state updates:
```python
# In mint/melt quote state update code:
await manager.notify("bolt11_mint_quote", quote.quote_id, quote.dict())
```

Steps:
1. Implement `SubscriptionManager` class for WebSocket connection tracking
2. Implement `GET /v1/ws` WebSocket endpoint accepting JSON-RPC messages
3. Handle `subscribe` and `unsubscribe` methods per NUT-17 spec
4. Call `manager.notify()` whenever quote state changes in NUT-04/05
5. Handle client disconnects gracefully

Reference: https://github.com/cashubtc/nuts/blob/main/17.md

## Acceptance Criteria

- [ ] WebSocket endpoint accepts connections at /v1/ws
- [ ] `subscribe` method accepted with `kind` and `filters` params
- [ ] Quote state changes push notifications to subscribed clients
- [ ] Client disconnect handled without crashing server
- [ ] NUT-17 listed as supported in GET /v1/info

## Notes

_Generated from feature_audit finding: NUT-17 WebSocket Subscriptions (high, effort: high). Marked long_running due to async complexity._
