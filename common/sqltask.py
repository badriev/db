"""Запуск SQL-решений ученика в тестах."""

import re
from pathlib import Path

import psycopg


def read_solution(path: Path) -> str | None:
    """Текст решения или None, если в файле только комментарии (задача не начата)."""
    if not path.exists():
        return None
    text = path.read_text()
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    code = re.sub(r"--[^\n]*", "", code)
    return text if code.strip(" \n\t;") else None


def run_query(conn: psycopg.Connection, sql: str, timeout_ms: int = 10_000):
    """Выполнить запрос в read-only транзакции (решение не может испортить данные) и откатить."""
    with conn.transaction(force_rollback=True), conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
        cur.execute(sql)
        if cur.description is None:
            raise AssertionError("запрос ничего не вернул — это должен быть SELECT")
        return [d.name for d in cur.description], cur.fetchall()
