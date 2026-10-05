import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        req_id = getattr(request.state, "request_id", "-")

        response = await call_next(request)

        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Do not log spammy polling or SSE events constantly
        if not request.url.path.endswith("/progress"):
            logger.info(
                f"[{req_id}] {request.method} {request.url.path} "
                f"-> status={response.status_code} duration={process_time:.2f}ms"
            )

        return response
