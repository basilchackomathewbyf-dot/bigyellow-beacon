"""Uniform error body: {"error": {"code": "...", "message": "..."}}."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        *,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}
        self.headers = headers
        super().__init__(message)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body: dict[str, Any] = {"code": exc.code, "message": exc.message, **exc.extra}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": body},
        headers=exc.headers,
    )
