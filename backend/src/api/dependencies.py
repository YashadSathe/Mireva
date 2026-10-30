"""API dependency providers for Mireva RAG foundation."""

from typing import Any, Dict, Optional

from db.session import get_db_session
from observability.logging import get_logger
from services.project_service import ProjectService
from storage.object import BaseObjectStorage, get_object_storage
from storage.vector import BaseVectorStore

logger = get_logger(__name__)


def get_vector_store_dependency() -> Optional[BaseVectorStore]:
    """Dependency provider returning default BaseVectorStore instance."""
    try:
        from storage.vector import get_vector_store

        return get_vector_store()
    except Exception:
        return None


def get_storage() -> BaseObjectStorage:
    """Dependency provider returning default BaseObjectStorage instance."""
    return get_object_storage()


def get_project_service() -> ProjectService:
    """Transitional dependency provider for ProjectService."""
    return ProjectService()


async def get_current_project(project_id: str) -> Dict[str, str]:
    """Transitional stub: accepts project_id without requiring legacy user/project tables."""
    return {"id": project_id}


def get_rag_service_dependency() -> "RAGService":
    """Dependency provider returning configured RAGService singleton instance."""
    from services.rag_service import get_rag_service

    return get_rag_service()


__all__ = [
    "get_db_session",
    "get_vector_store_dependency",
    "get_storage",
    "get_project_service",
    "get_current_project",
    "get_rag_service_dependency",
]
