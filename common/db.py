"""Подключения к учебным БД. Параметры берутся из окружения (.env подхватывает Makefile)."""

import os

import psycopg


def dsn(db: str | None = None) -> str:
    return (
        f"host={os.getenv('PG_HOST', 'localhost')} "
        f"port={os.getenv('PG_PORT', '55432')} "
        f"user={os.getenv('PG_USER', 'student')} "
        f"password={os.getenv('PG_PASSWORD', 'student')} "
        f"dbname={db or os.getenv('PG_DB', 'shop')}"
    )


def test_db_name() -> str:
    return os.getenv("PG_TEST_DB", "shop_test")


def connect(db: str | None = None, **kwargs) -> psycopg.Connection:
    """Соединение с фиксированным часовым поясом UTC — результаты с датами детерминированы."""
    conn = psycopg.connect(dsn(db), **kwargs)
    conn.execute("SET TimeZone = 'UTC'")
    conn.commit()
    return conn
