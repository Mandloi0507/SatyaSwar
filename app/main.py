"""
SatyaSwar - Main Application Entrypoint
Member 2: Backend, Infrastructure, Database and Security

This module initializes the FastAPI application, sets up CORS middleware based on
configured origins, defines core system lifecycle events via lifespan, and exposes
root and health-check endpoints.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events for the FastAPI application.
    NOTE: Firebase Admin SDK initialization will be added in M2.
    """
    # Startup: Load and validate settings
    _ = get_settings()
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


# Router registration placeholders for upcoming modules:
# M4: REST APIs & Session Management
# app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["Contacts"])
# app.include_router(calls_router, prefix="/api/v1/calls", tags=["Calls"])
# M7: Trusted-Contact Verification
# app.include_router(verification_router, prefix="/api/v1/verification", tags=["Verification"])
