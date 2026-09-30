"""Сверка результата запроса с эталоном без раскрытия самого эталона.

Эталон хранится как хеши строк. Значения нормализуются, чтобы 10 и 10.00 или
int и bigint не считались разными ответами; округление — до 2 знаков.
"""

import datetime as dt
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def _norm(v) -> str:
    if v is None:
        return "∅"
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, (int, float, Decimal)):
        d = Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return format(d.normalize() if d != 0 else Decimal(0), "f")
    if isinstance(v, dt.datetime):
        if v.tzinfo is not None:
            v = v.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return v.isoformat(sep=" ")
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, dt.timedelta):
        return str(v.total_seconds())
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_norm(x) for x in v) + "]"
    return str(v)


def row_hash(row) -> str:
    return hashlib.sha1("\x1f".join(_norm(v) for v in row).encode()).hexdigest()[:12]


def fingerprint(columns: list[str], rows: list[tuple]) -> dict:
    return {"columns": columns, "rows": [row_hash(r) for r in rows]}


def load_expected(path: Path) -> dict:
    return json.loads(path.read_text())


def compare(expected: dict, columns: list[str], rows: list[tuple], ordered: bool) -> str | None:
    """None — если совпало, иначе человекочитаемая подсказка, что не так."""
    exp_cols, exp_rows = expected["columns"], expected["rows"]
    if [c.lower() for c in columns] != exp_cols:
        return f"колонки: ожидались {exp_cols}, получены {columns}"
    got = [row_hash(r) for r in rows]
    if len(got) != len(exp_rows):
        return f"число строк: ожидалось {len(exp_rows)}, получено {len(got)}"
    if not ordered:
        if sorted(got) != sorted(exp_rows):
            bad = len(set(got) - set(exp_rows))
            return f"строки не совпадают: {bad} из {len(got)} строк отличаются от эталона"
        return None
    for i, (g, e) in enumerate(zip(got, exp_rows)):
        if g != e:
            in_set = g in set(exp_rows)
            hint = "строка есть в эталоне, но не на этом месте (проверь ORDER BY и тай-брейки)" if in_set else "такой строки в эталоне нет"
            return f"первое расхождение в строке #{i + 1}: {rows[i]!r} — {hint}"
    return None
