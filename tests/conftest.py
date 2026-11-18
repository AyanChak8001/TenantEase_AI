import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def db_session(tmp_path):
    # SQLite file is isolated per test and never touches the development DB.
    from database.db import create_test_session
    engine, session = create_test_session(f"sqlite:///{tmp_path / 'test.db'}")
    yield session
    session.close(); engine.dispose()
