"""Application entry point: wiring, middleware and error handling."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.errors import AppError
from app.logging_config import get_logger, setup_logging
from app.routers import admin, chat, health

setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Service started", extra={"extra_data": {
        "model": settings.openai_model,
    }})
    yield


app = FastAPI(
    title="Real Estate AI Assistant",
    description=(
        "Agentic backend for a real estate assistant. The LLM chooses which tool "
        "to call - there is no keyword routing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Tag every request so its logs can be traced end to end."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    started = time.time()

    response = await call_next(request)

    logger.info("Request handled", extra={"extra_data": {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.time() - started) * 1000, 1),
    }})
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Errors we raised on purpose, with a message safe to show a customer."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning("Handled error", extra={"extra_data": {
        "request_id": request_id,
        "error": exc.message,
    }})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request body.", "details": str(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Last resort. Log the stack trace, never send it to the client."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error", extra={"extra_data": {
        "request_id": request_id,
    }})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error.", "request_id": request_id},
    )
