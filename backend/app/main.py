from contextlib import asynccontextmanager
import logging
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter
from app.db.session import get_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger = configure_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting %s backend (env=%s, db_dialect=%s)",
        settings.APP_NAME,
        settings.APP_ENV,
        "sqlite" if settings.is_sqlite else "postgresql",
    )
    yield
    logger.info("Shutting down %s backend cleanly", settings.APP_NAME)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TerraQora AI API",
        description="Backend API foundation for TerraQora AI — Intelligence for Every Acre.",
        version="0.1.0",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SlowAPIMiddleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        formatted_errors: list[dict[str, Any]] = []
        messages: list[str] = []
        for err in exc.errors():
            loc_parts = [str(p) for p in err.get("loc", ()) if p != "body"]
            field = ".".join(loc_parts) if loc_parts else "request"
            msg = str(err.get("msg", "Invalid value"))
            formatted_errors.append(
                {
                    "field": field,
                    "message": msg,
                    "type": err.get("type", "value_error"),
                }
            )
            messages.append(f"{field}: {msg}")

        return JSONResponse(
            status_code=422,
            content={
                "detail": "; ".join(messages) if messages else "Request validation failed.",
                "errors": formatted_errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logging.getLogger("terraqora").exception("Unhandled server exception: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal server error occurred."},
        )

    @app.get("/health", tags=["Health"])
    def root_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connectivity check failed.",
            ) from exc

        return {
            "status": "ok",
            "service": "TerraQora AI API",
            "version": "0.1.0",
            "database": "connected",
        }

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
