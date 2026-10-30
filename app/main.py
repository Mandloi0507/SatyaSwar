"""
SatyaSwar - Main Application Entrypoint
Member 2: Backend, Infrastructure, Database and Security

This module initializes the FastAPI application, sets up CORS middleware based on
configured origins, defines core system lifecycle events via lifespan, and exposes
root and health-check endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.errors import SatyaSwarException
from app.routes.auth import router as auth_router
from app.routes.calls import router as calls_router
from app.routes.contacts import router as contacts_router
from app.routes.users import router as users_router
from app.services.firebase import init_firebase
from app.websocket.call_stream import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events for the FastAPI application.
    Initializes Firebase Admin SDK on application startup.
    """
    # Startup: Load and validate settings
    _ = get_settings()
    try:
        init_firebase()
    except Exception as e:
        logger.warning("Firebase Admin initialization deferred: %s", e)
    yield
    # Shutdown: Clean up external connections (if any)


settings = get_settings()

app = FastAPI(
    title="SatyaSwar API",
    version="0.1.0",
    description="Backend infrastructure for SatyaSwar",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS Middleware using normalized origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root() -> dict[str, str]:
    """Root endpoint to verify backend service availability."""
    return {"project": "SatyaSwar", "message": "Backend is running"}


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """
    Health check endpoint for container health probes and monitoring.
    Does not require Firebase authentication.
    """
    return {"status": "healthy"}


# Standard Error Envelope Exception Handlers (Section 9.5)
STATUS_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    410: "GONE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(SatyaSwarException)
async def satyaswar_exception_handler(request: Request, exc: SatyaSwarException) -> JSONResponse:
    """Handles explicit SatyaSwar application exceptions with standardized error codes."""
    payload = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }
    if exc.details is not None:
        payload["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Wraps FastAPI/Starlette HTTPExceptions in standard error envelope."""
    code = STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Wraps request schema validation failures in standard error envelope."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )


# M2: Authentication Routes
app.include_router(auth_router)

# M4: REST APIs & Session Management
app.include_router(users_router)
app.include_router(contacts_router)
app.include_router(calls_router)

# M5: WebSocket Audio Streaming
app.include_router(ws_router)

# M7: Trusted-Contact Verification (placeholder)
# app.include_router(verification_router, prefix="/api/v1/verification", tags=["Verification"])

