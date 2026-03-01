---
id: 4
title: "Bootstrap REST API server with routing and error handling"
priority: P0
severity: critical
status: completed
source: feature_audit
file: "cashu_mint/main.py"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: infrastructure
group_reason: "REST API server is the container for all NUT endpoint implementations"
---

# Bootstrap REST API server with routing and error handling

**Priority:** P0 (critical)
**Source:** feature_audit / gap_analyzer
**Location:** cashu_mint/main.py

## Problem

No REST API server exists. There is no HTTP server, routing, or request/response handling. None of the NUT endpoints can be served.

The Cashu mint requires a JSON REST API with specific endpoint paths and error response formats per the NUT specifications. Wallets connect to these endpoints to perform mint/melt/swap operations.

## How to Fix

Implement `cashu_mint/main.py` with FastAPI:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from cashu_mint.db.database import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(
    title="Cashu Mint",
    version="0.1.0",
    lifespan=lifespan
)

# Error response format per NUT specifications
@app.exception_handler(Exception)
async def cashu_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "code": getattr(exc, 'code', 10000)}
    )

# Include routers (add as NUTs are implemented)
# app.include_router(keys_router, prefix="/v1")
# app.include_router(keysets_router, prefix="/v1")
# app.include_router(mint_router, prefix="/v1")
# app.include_router(melt_router, prefix="/v1")
# app.include_router(swap_router, prefix="/v1")
# app.include_router(info_router, prefix="/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Steps:
1. Create `cashu_mint/main.py` with FastAPI app and lifespan handler
2. Create `cashu_mint/routers/` directory for NUT router modules
3. Implement standard Cashu error codes (see NUT spec error table)
4. Create a `CashuError` exception class with error codes
5. Add CORS middleware (mints are accessed from web wallets)
6. Configure uvicorn startup in `pyproject.toml` or a `run.py` script
7. Add request/response logging middleware

Error codes to implement per NUT-00:
- 10000: Unknown error
- 10001: Token is already spent
- 10002: Token is not verified
- 11001: Bolt11 payment failed
- 11002: Quote not paid

## Acceptance Criteria

- [ ] `uvicorn cashu_mint.main:app` starts successfully
- [ ] GET /health returns `{"status": "ok"}` with 200
- [ ] Unknown routes return 404 with JSON body
- [ ] Unhandled exceptions return structured JSON error (not HTML stack trace)
- [ ] CORS headers present for browser wallet compatibility
- [ ] Router structure in place for NUT modules

## Notes

_Generated from feature_audit finding: REST API Server (critical, blocking)._
