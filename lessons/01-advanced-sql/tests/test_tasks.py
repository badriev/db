from pathlib import Path

import pytest

from common.checker import compare, load_expected
from common.sqltask import read_solution, run_query

LESSON = Path(__file__).parents[1]
EXPECTED = load_expected(LESSON / "tests" / "expected.json")


@pytest.mark.parametrize("task", sorted(EXPECTED))
def test_task(task, test_conn):
    sql = read_solution(LESSON / "sql" / f"{task}.sql")
    if sql is None:
        pytest.skip("не решено")
    columns, rows = run_query(test_conn, sql)
    exp = EXPECTED[task]
    error = compare(exp, columns, rows, exp["ordered"])
    if error:
        pytest.fail(error, pytrace=False)
