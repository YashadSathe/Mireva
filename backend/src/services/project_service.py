"""Transitional stub for ProjectService during legacy cleanup phase."""

from typing import Any, Dict


class ProjectService:
    """Minimal stub to satisfy RAG retrieval endpoint dependencies without legacy models."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def get_project_by_id(self, project_id: str) -> Dict[str, str]:
        """Transitional stub: accepts project_id without database lookup."""
        return {"id": project_id}
