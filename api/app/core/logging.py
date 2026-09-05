import json
import logging
import sys
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("chargebackos")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_event(
    event: str,
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    case_id: str | None = None,
    batch_id: str | None = None,
    model_version: str | None = None,
    policy_version: str | None = None,
    outcome: str | None = None,
    duration_ms: float | None = None,
    error_type: str | None = None,
) -> None:
    payload = {
        "event": event,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "case_id": case_id,
        "batch_id": batch_id,
        "model_version": model_version,
        "policy_version": policy_version,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "error_type": error_type,
    }
    logger.info(json.dumps({k: v for k, v in payload.items() if v is not None}))


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                "http.error",
                request_id=request_id,
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            raise
        response.headers["x-request-id"] = request_id
        log_event(
            "http.request",
            request_id=request_id,
            correlation_id=correlation_id,
            outcome=str(response.status_code),
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        return response
