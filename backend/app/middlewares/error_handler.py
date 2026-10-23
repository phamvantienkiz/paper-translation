from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import logger


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            req_id = getattr(request.state, "request_id", "unknown")
            logger.exception(f"[{req_id}] Unhandled error occurred: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Đã xảy ra lỗi máy chủ nội bộ. Vui lòng kiểm tra log hệ thống.",
                        "details": str(exc),
                    },
                    "request_id": req_id,
                },
            )
