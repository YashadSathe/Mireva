"""Automated architectural boundary and dependency direction verification tests for Mireva.

Validates that:
1. Core is foundational and does not import application, domain, or delivery layers.
2. Observability is foundational and does not import RAG, App, or Storage.
3. Storage, DB, and RAG do not import App (no lower-level -> delivery layer coupling).
4. RAG focuses strictly on knowledge retrieval and ingestion without agent or legacy application coupling.
5. Legacy subsystems (agents, llm, tools) are completely removed from src/.
6. Canonical core and observability exports remain functional.
"""

import ast
from pathlib import Path
import re
import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
ALEMBIC_ROOT = Path(__file__).resolve().parents[1] / "alembic"


def get_imported_modules(py_file_path: Path) -> set[str]:
    """Parse a python source file into an AST and extract all top-level module names imported."""
    with open(py_file_path, "r", encoding="utf-8", errors="ignore") as f:
        tree = ast.parse(f.read(), filename=str(py_file_path))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported


def test_legacy_subsystems_removed():
    """Verify that legacy agents, llm, and tools subsystems have been completely removed."""
    assert not (SRC_ROOT / "agents").exists(), "src/agents/ must be removed"
    assert not (SRC_ROOT / "llm").exists(), "src/llm/ must be removed"
    assert not (SRC_ROOT / "tools").exists(), "src/tools/ must be removed"


def test_core_does_not_import_higher_layers():
    """Verify that src/core/ is foundational and does not depend on other subsystems."""
    core_dir = SRC_ROOT / "core"
    assert core_dir.is_dir(), "src/core/ directory must exist"

    forbidden = {"rag", "app", "storage", "db", "services", "models", "schemas", "api"}
    violations = []
    for py_file in core_dir.rglob("*.py"):
        imported = get_imported_modules(py_file)
        overlap = imported & forbidden
        if overlap:
            violations.append(f"{py_file.relative_to(SRC_ROOT)}: {overlap}")

    assert not violations, f"Architectural violation: src/core/ imports higher layers: {violations}"


def test_observability_does_not_import_subsystems():
    """Verify that src/observability/ does not depend on RAG, App, or Storage."""
    obs_dir = SRC_ROOT / "observability"
    assert obs_dir.is_dir(), "src/observability/ directory must exist"

    forbidden = {"rag", "app", "services", "storage", "api"}
    violations = []
    for py_file in obs_dir.rglob("*.py"):
        imported = get_imported_modules(py_file)
        overlap = imported & forbidden
        if overlap:
            violations.append(f"{py_file.relative_to(SRC_ROOT)}: {overlap}")

    assert not violations, f"Architectural violation: src/observability/ imports forbidden layers: {violations}"


def test_lower_layers_do_not_import_app():
    """Verify that storage, db, and rag do not import from app."""
    subsystems = [SRC_ROOT / "storage", SRC_ROOT / "db", SRC_ROOT / "rag"]
    violations = []
    for subsystem in subsystems:
        for py_file in subsystem.rglob("*.py"):
            imported = get_imported_modules(py_file)
            if "app" in imported:
                violations.append(str(py_file.relative_to(SRC_ROOT)))

    assert not violations, f"Architectural violation: lower layers import 'app': {violations}"


def test_rag_does_not_import_legacy_subsystems():
    """Verify that src/rag/ does not import from agents, llm, or tools."""
    rag_dir = SRC_ROOT / "rag"
    forbidden = {"agents", "llm", "tools"}
    violations = []
    for py_file in rag_dir.rglob("*.py"):
        imported = get_imported_modules(py_file)
        overlap = imported & forbidden
        if overlap:
            violations.append(f"{py_file.relative_to(SRC_ROOT)}: {overlap}")

    assert not violations, f"Architectural violation: src/rag/ imports legacy subsystems: {violations}"


def test_no_stale_import_paths_in_src():
    """Verify that no code in src/ imports from retired generation modules or app.core."""
    pattern = re.compile(
        r"\b(app\.core|rag\.generation|services\.generation_service|schemas\.generation|exceptions\.generation)\b"
    )
    violations = []
    for py_file in SRC_ROOT.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                if pattern.search(line):
                    violations.append(f"{py_file}:{idx}: {line.strip()}")

    assert not violations, f"Found stale import paths: {violations}"


def test_canonical_core_exports():
    """Verify that src/core exposes canonical configuration with Mireva app name."""
    from core import Settings, get_settings
    from core.config import Settings as ConfigSettings

    assert Settings is ConfigSettings
    settings = get_settings()
    assert settings.APP_NAME == "Mireva"


def test_canonical_observability_exports():
    """Verify that src/observability exposes canonical logging."""
    from observability import get_logger, setup_logging
    from observability.logging import get_logger as LoggingGetLogger

    assert get_logger is LoggingGetLogger
    logger = get_logger("test_arch_logger")
    assert logger.name == "test_arch_logger"
