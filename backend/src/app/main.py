from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import api_router
from core.config import get_settings
from db.session import dispose_engine
from exceptions.database import DatabaseError
from exceptions.retrieval import (
    EmptyQueryError,
    InvalidQueryError,
    ProjectBoundaryViolationError,
    QueryLengthExceededError,
    RetrievalError,
)
from exceptions.storage import StorageError
from exceptions.vector import VectorStoreError
from observability.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown events."""
    settings = get_settings()
    setup_logging()
    logger.info(
        "Starting %s (v%s) in '%s' environment",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)
    await dispose_engine()


def create_application() -> FastAPI:
    """FastAPI application factory for Mireva RAG Foundation."""
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Support environment-driven origins while keeping localhost development enabled
    allowed_origins = list(dict.fromkeys(settings.CORS_ORIGINS))

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After", "Content-Disposition", "X-Accel-Buffering"],
    )

    # --------------------------------------------------------------------------
    # Exception Handlers
    # --------------------------------------------------------------------------
    @application.exception_handler(InvalidQueryError)
    async def invalid_query_handler(request: Request, exc: InvalidQueryError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(EmptyQueryError)
    async def empty_query_handler(request: Request, exc: EmptyQueryError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(QueryLengthExceededError)
    async def query_length_handler(request: Request, exc: QueryLengthExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(ProjectBoundaryViolationError)
    async def project_boundary_violation_handler(
        request: Request, exc: ProjectBoundaryViolationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(RetrievalError)
    async def retrieval_error_handler(request: Request, exc: RetrievalError) -> JSONResponse:
        logger.error("Retrieval pipeline failure: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Retrieval pipeline failed: {exc.message}"},
        )

    @application.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
        logger.error("Storage error during request: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "An object storage operation failed. Please try again."},
        )

    @application.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        logger.error("Database error during request: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred. Please try again later."},
        )

    @application.exception_handler(VectorStoreError)
    async def vector_store_error_handler(request: Request, exc: VectorStoreError) -> JSONResponse:
        logger.error("Vector store error during request: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "A vector store operation failed. Please try again later."},
        )

    # --------------------------------------------------------------------------
    # API Routers
    # --------------------------------------------------------------------------
    application.include_router(api_router)

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        """Basic health check endpoint."""
        return {
            "status": "ok",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @application.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Root status endpoint."""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "environment": settings.ENVIRONMENT,
        }

    return application


app = create_application()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
