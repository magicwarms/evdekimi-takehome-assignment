"""Shared test setup.

The environment variables below are set BEFORE anything imports app.config, so
the whole test run points at a throwaway database and never touches app.db.
"""

import os
import tempfile

import pytest

TEST_DB = os.path.join(tempfile.mkdtemp(), "test.db")

os.environ["DATABASE_PATH"] = TEST_DB
os.environ["OPENAI_API_KEY"] = "test-key-never-used"
os.environ["MAX_TOOL_ITERATIONS"] = "5"


@pytest.fixture(autouse=True)
def fresh_db():
    """Give every test a clean, freshly seeded database."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    from app.seed import seed
    seed()

    yield
