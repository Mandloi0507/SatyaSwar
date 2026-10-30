"""
SatyaSwar - Standard Error Models & Exceptions
Member 2: Backend, Infrastructure, Database and Security

Defines the standard error response envelope {"error": {"code": ..., "message": ...}}
and custom domain exceptions.
"""

from typing import Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Inner error payload containing code and message."""

    code: str = Field(description="Machine-readable application error code")
    message: str = Field(description="Human-readable error description")
    details: Optional[Any] = Field(default=None, description="Optional field-level validation errors or metadata")


class ErrorResponse(BaseModel):
    """Standardized root error response envelope."""

    error: ErrorDetail


class SatyaSwarException(HTTPException):
    """Base domain exception carrying standard error code and message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details

