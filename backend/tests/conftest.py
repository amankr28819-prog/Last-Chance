import os
import pytest
import sqlite3
from backend.database import init_db, get_connection

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_DIR = os.path.join(TEST_DIR, "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)

@pytest.fixture
def test_db(request):
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    db_file = os.path.join(SCRATCH_DIR, f"{test_name}.db")
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
    init_db(db_file)
    conn = get_connection(db_file)
    yield conn
    conn.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
