"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cashu_mint.config import settings
from cashu_mint.db.base import AsyncSessionLocal, create_all_tables
from cashu_mint.exceptions import CashuError

# Import ORM models so they register with Base.metadata before create_all_tables().
import cashu_mint.db.keyset_models  # noqa: F401
import cashu_mint.db.models  # noqa: F401


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    await create_all_tables()
    # Initialize keysets (creates one if none exist).
    from cashu_mint.nuts.keyset_manager import initialize_keysets

    async with AsyncSessionLocal() as db:
        await initialize_keysets(db)
    yield


app = FastAPI(
    title="Cashu Mint",
    description=settings.mint_description,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Error handlers — structured JSON for all errors per NUT spec
# ---------------------------------------------------------------------------


@app.exception_handler(CashuError)
async def cashu_error_handler(request: Request, exc: CashuError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "code": 10000},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# NUT-01 / NUT-02: keyset and public key endpoints
from cashu_mint.routers.keys import router as keys_router  # noqa: E402
from cashu_mint.routers.admin import router as admin_router  # noqa: E402

app.include_router(keys_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "mint": settings.mint_name}


def start() -> None:
    """Entry point for `cashu-mint` CLI command."""
    uvicorn.run(
        "cashu_mint.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    start()
