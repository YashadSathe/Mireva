"""API routes package exports."""

from fastapi import APIRouter

from api.retrieval import router as retrieval_router

api_router = APIRouter()
api_router.include_router(retrieval_router)

__all__ = [
    "api_router",
    "retrieval_router",
]
