"""
Main FastAPI application entrypoint for the Collaborative AI Agent Orchestration Framework.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.config.logging_config import setup_logging
from src.db.session import init_db
from src.api.routes import router as tasks_router
from src.api.websocket import ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown routines."""
    setup_logging()
    logger.info("Initializing application and database schemas...")
    try:
        await init_db()
        logger.info("Database schemas ready.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Collaborative AI Agent Orchestration Framework",
    description="Multi-agent orchestration system with LangGraph, Celery, Redis, PostgreSQL, and FastAPI WebSockets.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Returns 200 OK for container and service readiness probes.",
)
async def health_check():
    return {"status": "ok", "service": "agent-orchestrator-api"}


# Mount API and WebSocket routers
app.include_router(tasks_router, prefix="/api/v1", tags=["Tasks"])
app.include_router(ws_router, tags=["WebSockets"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main.py:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )
