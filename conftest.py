import pytest

from common.db import connect, test_db_name
from datasets.generator import GENERATOR_VERSION, generate


@pytest.fixture(scope="session")
def test_conn():
    """Соединение с тестовой БД; при отсутствии/устаревании датасета он перегенерируется."""
    db = test_db_name()
    conn = connect(db)
    try:
        meta = dict(conn.execute("SELECT key, value FROM _meta").fetchall())
    except Exception:
        conn.rollback()
        meta = {}
    if meta.get("scale") != "tiny" or meta.get("generator_version") != GENERATOR_VERSION:
        conn.close()
        generate(db, "tiny", 42)
        conn = connect(db)
    yield conn
    conn.close()
