"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cashu_mint.config import settings
from cashu_mint.db.base import create_all_tables


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    await create_all_tables()
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
