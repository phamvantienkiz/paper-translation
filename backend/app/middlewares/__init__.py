from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.middlewares.cors import get_cors_config
from app.middlewares.error_handler import ErrorHandlingMiddleware
from app.middlewares.logging import RequestLoggingMiddleware
from app.middlewares.request_id import RequestIDMiddleware


def register_middlewares(app: FastAPI) -> None:
    # Outermost catches all errors
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(CORSMiddleware, **get_cors_config())
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
