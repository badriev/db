"""Генератор синтетического маркетплейса.

    python -m datasets.generator --scale small --db shop

Данные детерминированы: один и тот же seed и scale дают байт-в-байт одинаковую БД —
на этом держатся автотесты (они гоняются на scale=tiny в отдельной БД shop_test).

Загрузка идёт через COPY — самый быстрый способ залить данные в PostgreSQL.
Заказы, позиции, платежи и отзывы генерируются одним проходом, поэтому пишутся
параллельно через четыре соединения (у одного соединения активен только один COPY).
Внешние ключи создаются после загрузки — см. constraints.sql.
"""

import argparse
import bisect
import datetime as dt
import itertools
import random
import time
from pathlib import Path

from common.db import connect

GENERATOR_VERSION = "1"
HERE = Path(__file__).parent

START = dt.datetime(2023, 1, 1, tzinfo=dt.timezone.utc)
END = dt.datetime(2025, 7, 1, tzinfo=dt.timezone.utc)
SPAN = int((END - START).total_seconds())
EVENTS_START = int((dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc) - START).total_seconds())
DAY = 86400

SCALES = {
    #          users   sellers products  orders    sessions
    "tiny":   (300,    15,     250,      1_500,    1_500),
    "small":  (20_000, 300,    10_000,   100_000,  100_000),
    "medium": (200_000, 2_000, 100_000,  1_000_000, 1_000_000),
    "large":  (2_000_000, 10_000, 500_000, 10_000_000, 10_000_000),
}

COUNTRIES = {
    "RU": (50, ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург"]),
    "KZ": (12, ["Алматы", "Астана", "Шымкент"]),
    "BY": (10, ["Минск", "Гродно", "Брест"]),
    "AM": (6, ["Ереван", "Гюмри"]),
    "GE": (6, ["Тбилиси", "Батуми"]),
    "RS": (6, ["Белград", "Нови-Сад"]),
    "TR": (5, ["Стамбул", "Анкара", "Анталья"]),
    "DE": (5, ["Берлин", "Мюнхен", "Гамбург"]),
}
COUNTRY_CODES = list(COUNTRIES)
COUNTRY_W = [w for w, _ in COUNTRIES.values()]

FIRST = ["Алексей", "Мария", "Иван", "Анна", "Дмитрий", "Елена", "Сергей", "Ольга",
         "Артём", "Наталья", "Тимур", "Айгерим", "Арман", "Нино", "Давид", "Милош"]
LAST = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Ахметов",
        "Саргсян", "Беридзе", "Петрович", "Новиков", "Морозов", "Волков", "Козлов"]

# (id, name, parent_id); пустой корень 25 без товаров — пригодится для LEFT JOIN.
CATEGORIES = [
    (1, "Электроника", None),
    (2, "Смартфоны и гаджеты", 1),
    (3, "Смартфоны", 2),
    (4, "Умные часы", 2),
    (5, "Аксессуары для телефонов", 2),
    (6, "Компьютеры", 1),
    (7, "Ноутбуки", 6),
    (8, "Мониторы", 6),
    (9, "Комплектующие", 6),
    (10, "Видеокарты", 9),
    (11, "Накопители", 9),
    (12, "Дом и кухня", None),
    (13, "Кухня", 12),
    (14, "Посуда", 13),
    (15, "Техника для кухни", 13),
    (16, "Текстиль", 12),
    (17, "Книги", None),
    (18, "Художественная литература", 17),
    (19, "Техническая литература", 17),
    (20, "Программирование", 19),
    (21, "Базы данных", 20),
    (22, "Спорт", None),
    (23, "Велоспорт", 22),
    (24, "Бег", 22),
    (25, "Подарочные сертификаты", None),
]
# категория -> (вес в ассортименте, min цена, max цена)
PRODUCT_CATS = {
    3: (8, 150, 1800), 4: (4, 80, 700), 5: (12, 3, 60), 7: (6, 400, 3500),
    8: (4, 120, 1200), 10: (3, 250, 2500), 11: (5, 30, 400), 14: (10, 5, 150),
    15: (6, 30, 900), 16: (7, 8, 120), 18: (10, 4, 40), 20: (6, 15, 90),
    21: (3, 20, 110), 23: (4, 50, 2500), 24: (6, 10, 250),
}
BRANDS = ["Nova", "Orbit", "Kvant", "Sever", "Altai", "Polar", "Delta", "Vega", "Ural", "Zenit"]

PROMOS = ["WELCOME10", "SUMMER24", "BLACKFRIDAY", "VIP"]
REVIEW_TEXTS = ["Отлично", "Всё как в описании", "Быстрая доставка", "Качество так себе",
                "Не рекомендую", "Рекомендую", "Цена завышена", "Лучшая покупка года"]


def ts(seconds: int) -> dt.datetime:
    return START + dt.timedelta(seconds=seconds)


def poisson_times(rnd: random.Random, n: int, lo: int, hi: int):
    """n отсортированных моментов времени в [lo, hi) без сортировки в памяти."""
    rate = n / (hi - lo)
    t = float(lo)
    for _ in range(n):
        t += rnd.expovariate(rate)
        yield min(int(t), hi - 1)


def pareto_cum(rnd: random.Random, n: int, alpha: float) -> list[float]:
    """Кумулятивные веса с тяжёлым хвостом: немногие элементы популярны, большинство — нет."""
    return list(itertools.accumulate(rnd.paretovariate(alpha) for _ in range(n)))


def pick(rnd: random.Random, cum: list[float], upto: int | None = None) -> int:
    """Индекс по кумулятивным весам; upto ограничивает выбор префиксом."""
    hi = len(cum) if upto is None else upto
    return bisect.bisect_right(cum, rnd.random() * cum[hi - 1], 0, hi - 1)


def money(x: float) -> str:
    return f"{x:.2f}"


def generate(db: str, scale: str, seed: int) -> None:
    n_users, n_sellers, n_products, n_orders, n_sessions = SCALES[scale]
    rnd = random.Random(seed)
    t0 = time.monotonic()

    def log(msg: str) -> None:
        print(f"[{time.monotonic() - t0:7.1f}s] {msg}", flush=True)

    main = connect(db)
    main.execute((HERE / "schema.sql").read_text())
    main.commit()
    log(f"схема создана в {db}, scale={scale}")

    # --- users ---------------------------------------------------------------
    user_created: list[int] = []
    user_country: list[str] = []
    with main.cursor() as cur, cur.copy(
        "COPY users (id, email, full_name, country, city, referred_by, created_at) FROM STDIN"
    ) as cp:
        for uid, t in enumerate(poisson_times(rnd, n_users, 0, SPAN - 30 * DAY), start=1):
            country = rnd.choices(COUNTRY_CODES, COUNTRY_W)[0]
            city = None if rnd.random() < 0.1 else rnd.choice(COUNTRIES[country][1])
            ref = None
            if uid > 1 and rnd.random() < 0.3:
                # половина рефералов — от «свежих» пользователей: получаются длинные цепочки
                lo = max(1, uid - max(2, uid // 20)) if rnd.random() < 0.5 else 1
                ref = rnd.randint(lo, uid - 1)
            cp.write_row((uid, f"user{uid}@example.com",
                          f"{rnd.choice(FIRST)} {rnd.choice(LAST)}",
                          country, city, ref, ts(t)))
            user_created.append(t)
            user_country.append(country)
    main.commit()
    log(f"users: {n_users}")

    main.cursor().executemany(
        "INSERT INTO categories (id, name, parent_id) VALUES (%s, %s, %s)", CATEGORIES)

    seller_start = -2 * 365 * DAY
    with main.cursor() as cur, cur.copy("COPY sellers (id, name, country, created_at) FROM STDIN") as cp:
        for sid in range(1, n_sellers + 1):
            cp.write_row((sid, f"Продавец {sid}", rnd.choices(COUNTRY_CODES, COUNTRY_W)[0],
                          ts(rnd.randint(seller_start, -365 * DAY))))

    # --- products ------------------------------------------------------------
    cat_ids = list(PRODUCT_CATS)
    cat_w = [PRODUCT_CATS[c][0] for c in cat_ids]
    cat_name = {c[0]: c[1] for c in CATEGORIES}
    seller_cum = pareto_cum(rnd, n_sellers, 1.2)
    product_price: list[float] = []
    with main.cursor() as cur, cur.copy(
        "COPY products (id, seller_id, category_id, name, price, is_active, created_at) FROM STDIN"
    ) as cp:
        for pid in range(1, n_products + 1):
            cat = rnd.choices(cat_ids, cat_w)[0]
            _, lo, hi = PRODUCT_CATS[cat]
            price = round(lo * (hi / lo) ** rnd.random(), 2)  # лог-равномерно
            product_price.append(price)
            cp.write_row((pid, pick(rnd, seller_cum) + 1, cat,
                          f"{cat_name[cat]} {rnd.choice(BRANDS)} {rnd.randint(100, 999)}",
                          money(price), rnd.random() > 0.1,
                          ts(rnd.randint(-365 * DAY, -DAY))))
    main.commit()
    log(f"categories: {len(CATEGORIES)}, sellers: {n_sellers}, products: {n_products}")

    # --- orders + order_items + payments + reviews ---------------------------
    # 15% пользователей никогда ничего не покупают: вес 0.
    user_cum = list(itertools.accumulate(
        0.0 if rnd.random() < 0.15 else rnd.paretovariate(1.5) for _ in range(n_users)))
    product_cum = pareto_cum(rnd, n_products, 1.1)

    conns = {name: connect(db) for name in ("items", "payments", "reviews")}
    cur_o, cur_i, cur_p, cur_r = (main.cursor(), conns["items"].cursor(),
                                  conns["payments"].cursor(), conns["reviews"].cursor())
    payment_id = review_id = 0
    reviewed: set[int] = set()
    n_items = 0
    first_order = user_created[0] + DAY
    with (cur_o.copy("COPY orders (id, user_id, status, shipping_country, promo_code, created_at) FROM STDIN") as co,
          cur_i.copy("COPY order_items (order_id, product_id, quantity, unit_price) FROM STDIN") as ci,
          cur_p.copy("COPY payments (id, order_id, method, status, amount, created_at) FROM STDIN") as cpay,
          cur_r.copy("COPY reviews (id, user_id, product_id, rating, body, created_at) FROM STDIN") as crev):
        for oid, t in enumerate(poisson_times(rnd, n_orders, first_order, SPAN), start=1):
            # покупатель — только из зарегистрированных к моменту t
            eligible = bisect.bisect_right(user_created, t)
            while user_cum[eligible - 1] == 0.0:  # вырожденный случай на крошечных масштабах
                eligible += 1
            uid = pick(rnd, user_cum, eligible) + 1

            age = SPAN - t
            if age > 30 * DAY:
                status = rnd.choices(["delivered", "cancelled", "refunded", "shipped"], [76, 16, 6, 2])[0]
            else:
                status = rnd.choices(["created", "paid", "shipped", "delivered", "cancelled"],
                                     [15, 20, 30, 20, 15])[0]
            country = user_country[uid - 1] if rnd.random() < 0.92 else rnd.choice(COUNTRY_CODES)
            promo = None
            if rnd.random() < 0.2:
                promo = rnd.choice(PROMOS)
                if rnd.random() < 0.1:
                    promo = promo.lower()  # грязные данные из старого клиента
            co.write_row((oid, uid, status, country, promo, ts(t)))

            k = rnd.choices([1, 2, 3, 4, 5], [50, 25, 13, 7, 5])[0]
            products = set()
            while len(products) < k:
                products.add(pick(rnd, product_cum) + 1)
            total = 0.0
            for pid in sorted(products):
                qty = rnd.choices([1, 2, 3], [80, 15, 5])[0]
                unit = round(product_price[pid - 1] * (0.9 if promo else 1.0), 2)
                total += qty * unit
                ci.write_row((oid, pid, qty, money(unit)))
            n_items += k
            total = round(total, 2)

            method = rnd.choices(["card", "sbp", "wallet"], [60, 30, 10])[0]
            pt = t + rnd.randint(30, 600)
            if status in ("paid", "shipped", "delivered", "refunded"):
                if rnd.random() < 0.15:
                    payment_id += 1
                    cpay.write_row((payment_id, oid, method, "failed", money(total), ts(pt)))
                    pt += rnd.randint(30, 900)
                payment_id += 1
                cpay.write_row((payment_id, oid, method, "succeeded", money(total), ts(pt)))
                if status == "delivered" and rnd.random() < 0.01:
                    payment_id += 1  # двойное списание — баг интеграции с эквайрингом
                    cpay.write_row((payment_id, oid, method, "succeeded", money(total), ts(pt + rnd.randint(1, 5))))
                if status == "refunded":
                    payment_id += 1
                    cpay.write_row((payment_id, oid, method, "refunded", money(total),
                                    ts(min(pt + rnd.randint(DAY, 20 * DAY), SPAN - 1))))
            elif status == "cancelled" and rnd.random() < 0.4:
                payment_id += 1
                cpay.write_row((payment_id, oid, method, "failed", money(total), ts(pt)))

            if status == "delivered":
                for pid in sorted(products):
                    key = uid * 10_000_000 + pid
                    if key in reviewed or rnd.random() >= 0.25:
                        continue
                    reviewed.add(key)
                    review_id += 1
                    rating = rnd.choices([1, 2, 3, 4, 5], [5, 5, 10, 30, 50])[0]
                    body = rnd.choice(REVIEW_TEXTS) if rnd.random() < 0.6 else None
                    crev.write_row((review_id, uid, pid, rating, body,
                                    ts(min(t + rnd.randint(3 * DAY, 30 * DAY), SPAN - 1))))
    main.commit()
    for c in conns.values():
        c.commit()
        c.close()
    log(f"orders: {n_orders}, order_items: {n_items}, payments: {payment_id}, reviews: {review_id}")

    # --- events --------------------------------------------------------------
    eid = 0
    with main.cursor() as cur, cur.copy(
        "COPY events (id, session_id, user_id, event_type, product_id, created_at) FROM STDIN"
    ) as cp:
        for sid, t in enumerate(poisson_times(rnd, n_sessions, EVENTS_START, SPAN - DAY), start=1):
            uid = None
            if rnd.random() < 0.7:
                eligible = bisect.bisect_right(user_created, t)
                uid = rnd.randint(1, max(1, eligible))
            viewed = []
            for _ in range(rnd.choices(range(1, 9), [30, 20, 15, 10, 10, 6, 5, 4])[0]):
                pid = pick(rnd, product_cum) + 1
                viewed.append(pid)
                eid += 1
                cp.write_row((eid, sid, uid, "view", pid, ts(t)))
                t += rnd.randint(10, 300)
            cart = [p for p in dict.fromkeys(viewed) if rnd.random() < 0.3]
            for pid in cart:
                eid += 1
                cp.write_row((eid, sid, uid, "add_to_cart", pid, ts(t)))
                t += rnd.randint(5, 120)
            if cart and rnd.random() < 0.4:
                eid += 1
                cp.write_row((eid, sid, uid, "checkout", None, ts(t)))
                t += rnd.randint(20, 600)
                if rnd.random() < 0.7:
                    eid += 1
                    cp.write_row((eid, sid, uid, "purchase", None, ts(t)))
    main.commit()
    log(f"events: {eid} в {n_sessions} сессиях")

    main.cursor().executemany(
        "INSERT INTO _meta (key, value) VALUES (%s, %s)",
        [("scale", scale), ("seed", str(seed)), ("generator_version", GENERATOR_VERSION)])
    main.commit()

    main.autocommit = True
    main.execute((HERE / "constraints.sql").read_text())
    main.close()
    log("внешние ключи созданы, ANALYZE выполнен — готово")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", choices=SCALES, default="small")
    ap.add_argument("--db", default=None, help="имя БД (по умолчанию PG_DB)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    generate(args.db, args.scale, args.seed)


if __name__ == "__main__":
    main()
