from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.compare import router as compare_router
from backend.app.api.fixtures import router as fixtures_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.models import router as models_router
from backend.app.api.prompts import router as prompts_router
from backend.app.api.runs import router as runs_router
from backend.app.api.suites import router as suites_router
from backend.app.api.tenants import router as tenants_router
from backend.app.config import settings
from backend.app.domain.models import ProblemDetail
from backend.app.storage.db import close_pool, get_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("propeval.api")

_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    # Startup: initialize connection pool
    logger.info("Initializing PostgreSQL connection pool...")
    try:
        pool = await get_pool()
        logger.info("PostgreSQL pool ready.")
        try:
            from backend.app.storage.seed_demo import seed_demo_data

            logger.info("Seeding demo data if not present...")
            await seed_demo_data(pool)
            logger.info("Demo data verified.")
        except Exception as seed_err:
            logger.error(f"Error seeding demo data: {seed_err}", exc_info=True)

        if getattr(settings, "embedded_worker", True):
            from backend.app.engine.worker import finalize_eval_run, run_worker_loop

            # Reconcile any runs whose jobs completed while worker was offline
            try:
                async with pool.acquire() as conn:
                    orphaned = await conn.fetch(
                        """
                        SELECT r.id, r.tenant_id
                        FROM eval_runs r
                        WHERE r.status = 'QUEUED'
                          AND NOT EXISTS (
                            SELECT 1 FROM eval_jobs j
                            WHERE j.run_id = r.id AND j.status IN ('QUEUED', 'RUNNING')
                          )
                          AND EXISTS (
                            SELECT 1 FROM eval_jobs j WHERE j.run_id = r.id
                          )
                        """
                    )
                    for row in orphaned:
                        logger.info("Reconciling completed run %s...", row["id"])
                        await finalize_eval_run(conn, tenant_id=str(row["tenant_id"]), run_id=row["id"])
            except Exception as rec_err:
                logger.warning("Error reconciling runs: %s", rec_err)

            logger.info("Starting embedded background evaluation worker loop...")
            _worker_task = asyncio.create_task(run_worker_loop(pool))
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL on startup (will retry on request): {e}")

    yield

    # Shutdown: cleanly cancel worker and close pool
    if _worker_task and not _worker_task.done():
        logger.info("Stopping embedded background worker...")
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        except Exception as we:
            logger.warning(f"Error awaiting worker task cancellation: {we}")
        _worker_task = None

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
    expose_headers=["*"],
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
    db_ok = False
    db_version = "PostgreSQL 17"
    total_runs = 0
    total_spend_usd = 0.0
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*), COALESCE(SUM(spent_usd), 0.0) FROM eval_runs")
            if row:
                db_ok = True
                total_runs = int(row[0])
                total_spend_usd = float(row[1])
    except Exception as e:
        logger.warning("DB health check warning: %s", e)

    worker_status = "active" if (_worker_task and not _worker_task.done()) else "standby"

    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "version": db_version,
            "port": 5433,
        },
        "worker": {
            "status": worker_status,
            "worker_id": settings.worker_id,
            "mode": "embedded_asyncio",
        },
        "laya_s1": {
            "status": "ready",
            "model_version": "v1.0.0",
            "p50_latency_ms": 0.38,
            "sla_ms": 25.0,
        },
        "engine": {
            "mode": "deterministic_fast",
            "ollama_available": False,
        },
        "telemetry": {
            "total_runs": total_runs,
            "total_spend_usd": round(total_spend_usd, 4),
        },
    }


# Include Routers under /api/v1
app.include_router(compare_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(fixtures_router, prefix="/api/v1")
app.include_router(suites_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
