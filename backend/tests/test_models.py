"""Unit and integration tests for the Mireva relational data model (ChunkModel).

Tests coverage:
- Model registration in Base.metadata
- Table definitions, column types, nullability, defaults
- Decoupling from legacy application foreign keys
- Compatibility and regression checks for ChunkModel
- In-memory persistence, queries, and serialization
"""

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import models
from models import Base, ChunkModel


@pytest.fixture
def memory_db():
    """In-memory SQLite database engine and session fixture."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


# ==============================================================================
# 1. Model Registration & Export Tests
# ==============================================================================


def test_model_registration_in_metadata():
    """Verify chunks table is registered with Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    assert "chunks" in table_names, f"chunks table missing from metadata: {table_names}"


def test_models_package_exports():
    """Verify models.__init__.py exports Base and ChunkModel."""
    expected_symbols = [
        "Base",
        "ChunkModel",
    ]
    for sym in expected_symbols:
        assert hasattr(models, sym), f"models package missing symbol '{sym}'"
        assert sym in models.__all__, f"'{sym}' not declared in models.__all__"


# ==============================================================================
# 2. Table Structure & Decoupled Column Integrity Tests
# ==============================================================================


def test_chunk_model_structure_and_decoupling():
    """Verify ChunkModel preserves all chunk attributes and is decoupled from legacy FKs."""
    table = Base.metadata.tables["chunks"]

    # Preserved columns
    required_cols = [
        "chunk_id",
        "project_id",
        "document_id",
        "document_version_id",
        "content",
        "contextual_content",
        "chunk_index",
        "heading",
        "heading_level",
        "section_path",
        "parent_element_id",
        "parent_chunk_id",
        "element_types",
        "metadata",
        "created_at",
        "updated_at",
    ]
    for col in required_cols:
        assert col in table.c, f"ChunkModel table missing column: {col}"

    # Nullability preservation
    assert not table.c.chunk_id.nullable
    assert table.c.project_id.nullable
    assert table.c.document_id.nullable
    assert table.c.document_version_id.nullable, "document_version_id must remain nullable"

    # Decoupling: Verify no foreign keys exist on project_id, document_id, document_version_id
    assert len(table.c.project_id.foreign_keys) == 0, "project_id must be decoupled from legacy FKs"
    assert len(table.c.document_id.foreign_keys) == 0, "document_id must be decoupled from legacy FKs"
    assert len(table.c.document_version_id.foreign_keys) == 0, "document_version_id must be decoupled from legacy FKs"

    # Compatibility properties
    chunk = ChunkModel(
        chunk_id="chunk_1",
        project_id="proj_1",
        document_id="doc_1",
        document_version_id="ver_1",
        content="verbatim content",
        contextual_content="enriched contextual content",
        chunk_index=3,
        heading="Introduction",
        heading_level=1,
        section_path=["Root", "Intro"],
        chunk_metadata={"token_count": 42},
    )
    assert chunk.text == "verbatim content"
    assert chunk.chunk_text == "verbatim content"
    assert chunk.index == 3
    assert chunk.meta == {"token_count": 42}

    d = chunk.to_dict()
    assert d["chunk_id"] == "chunk_1"
    assert d["content"] == "verbatim content"
    assert d["chunk_text"] == "verbatim content"
    assert d["index"] == 3
    assert d["heading"] == "Introduction"
    assert d["metadata"] == {"token_count": 42}


def test_chunk_model_database_crud(memory_db: Session):
    """Verify persisting and querying ChunkModel in relational database."""
    chunk = ChunkModel(
        chunk_id="chk_test_100",
        project_id="p_alpha",
        document_id="d_doc1",
        document_version_id="v_v1",
        content="Mireva RAG decoupled architecture test content.",
        contextual_content="Full context for Mireva RAG test.",
        chunk_index=0,
        heading="Mireva Core",
        heading_level=2,
        section_path=["Overview", "Mireva Core"],
        chunk_metadata={"source": "test", "tokens": 15},
    )
    memory_db.add(chunk)
    memory_db.commit()

    # Query back
    stored = memory_db.query(ChunkModel).filter_by(chunk_id="chk_test_100").first()
    assert stored is not None
    assert stored.project_id == "p_alpha"
    assert stored.document_id == "d_doc1"
    assert stored.document_version_id == "v_v1"
    assert stored.content == "Mireva RAG decoupled architecture test content."
    assert stored.heading == "Mireva Core"
    assert stored.meta == {"source": "test", "tokens": 15}

    # Delete
    memory_db.delete(stored)
    memory_db.commit()
    assert memory_db.query(ChunkModel).filter_by(chunk_id="chk_test_100").count() == 0
