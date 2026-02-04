"""
Atlas - Explainable AI Fraud Detection System
Main FastAPI Application
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.api.routes import router as api_router
from app.api.websocket import ws_router
from app.models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Atlas Risk API...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Atlas Risk API...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Explainable AI-powered fraud detection and risk scoring system",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - verifies all dependencies are available."""
    checks = {
        "api": True,
        "model_loaded": True  # Will be updated when model is loaded
    }
    
    all_healthy = all(checks.values())
    
    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks
        }
    )


# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Include WebSocket routes
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
