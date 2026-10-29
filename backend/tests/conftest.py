"""
Pytest configuration and fixtures.

Tests that require Exasol are marked with @pytest.mark.requires_db.
When no live Exasol connection is available, those tests are
reported as BLOCKED (not FAILED) via a skip.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure 'backend' directory is on sys.path so tests can `import app.*`
_BACKEND_DIR = Path(__file__).parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ── Paths ─────────────────────────────────────────────────────────────────────
SYNTHETIC_DIR = Path(__file__).parents[2] / "data" / "synthetic"
EXPECTED_FILE = Path(__file__).parents[2] / "data" / "expected" / "expected_outputs.json"


# ── Marks ─────────────────────────────────────────────────────────────────────
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring a live Exasol connection"
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker("requires_db"):
        if not _can_reach_exasol():
            pytest.skip(
                "BLOCKED: Exasol Personal not reachable. "
                "Start Exasol via 'irm https://www.exasol.com/install/starter-kit.ps1 | iex' "
                "and set EXASOL_HOST/PORT/USER/PASSWORD in .env."
            )


def _can_reach_exasol() -> bool:
    """Quick TCP-level check using the app's configured database endpoint."""
    import socket
    from app.core.config import get_settings

    settings = get_settings()
    try:
        with socket.create_connection(
            (settings.exasol_host, settings.exasol_port), timeout=2
        ):
            return True
    except OSError:
        return False


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def expected_outputs() -> dict:
    """Load the Python-calculated expected outputs for comparison with Exasol."""
    if not EXPECTED_FILE.exists():
        pytest.skip("expected_outputs.json not found — run generate_dataset.py first")
    return json.loads(EXPECTED_FILE.read_text())


@pytest.fixture(scope="session")
def synthetic_dir() -> Path:
    return SYNTHETIC_DIR


@pytest.fixture
def mock_conn():
    """A mock pyexasol connection for unit tests that don't need a live DB."""
    return MagicMock()


@pytest.fixture(scope="session")
def live_conn():
    """
    Session-scoped live Exasol connection.
    Only created when requires_db tests actually run (guarded by skip above).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1]))
    from app.db.connection import get_db
    from app.db.schema_init import init_schema
    from app.db.seed_loader import load_synthetic_data
    from app.core.config import get_settings

    settings = get_settings()
    with get_db() as conn:
        init_schema(conn, settings.exasol_schema)
        load_synthetic_data(conn, force_reload=False)
        yield conn
