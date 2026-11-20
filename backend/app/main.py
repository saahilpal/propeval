from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.fixtures import router as fixtures_router
from backend.app.api.prompts import router as prompts_router
from backend.app.api.runs import router as runs_router
from backend.app.api.suites import router as suites_router
from backend.app.api.tenants import router as tenants_router
from backend.app.config import settings
from backend.app.domain.models import ProblemDetail
from backend.app.storage.db import close_pool, get_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("propeval.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connection pool
    logger.info("Initializing PostgreSQL connection pool...")
    try:
        await get_pool()
        logger.info("PostgreSQL pool ready.")
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL on startup (will retry on request): {e}")

    yield

    # Shutdown: cleanly close pool
    logger.info("Closing PostgreSQL connection pool...")
    await close_pool()
    logger.info("Pool closed.")


app = FastAPI(
    title="PropEval API",
    description="Evaluation & Prompt Regression Workbench for Real-Estate Voice AI Agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# RFC 9457 Problem Details Exception Handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    problem = ProblemDetail(
        type=f"https://propeval.ai/errors/{exc.status_code}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    problem = ProblemDetail(
        type="https://propeval.ai/errors/internal-server-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected internal error occurred. Please check logs.",
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=500,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
    }


# Include Routers under /api/v1
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(fixtures_router, prefix="/api/v1")
app.include_router(suites_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
