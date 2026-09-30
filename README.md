# Базы данных: OLTP → OLAP → NoSQL

Практический курс уровня энтерпрайза и бигтеха: не «как написать запрос», а почему СУБД ведёт себя
так, как ведёт, и как проектировать хранение данных под реальную нагрузку. Python (`psycopg` и
нативные драйверы, без ORM) + чистый SQL, всё окружение в Docker.

Каждый урок: глубокая теория → задачи с автопроверкой → исследования на больших данных → ревью решений.
Уроки появляются по одному, по мере прохождения — следующий подстраивается под найденные пробелы.

## Быстрый старт

```bash
make install && make up-oltp && make seed-test && make seed SCALE=small
make psql            # консоль к учебной БД
make test L=01       # проверить решения урока
```

Подробно — [lessons/00-setup](lessons/00-setup/README.md).

## Программа (~14 недель при 20+ ч/нед)

### Часть I. SQL и OLTP — PostgreSQL
- [x] [00 — Окружение](lessons/00-setup/README.md)
- [ ] [01 — Продвинутый SQL: NULL, JOIN, окна, рекурсия](lessons/01-advanced-sql/README.md)
- [ ] 02 — Моделирование OLTP: нормальные формы, ключи, ограничения как инварианты
- [ ] 03 — Хранение в PostgreSQL: страницы, кортежи, TOAST, HOT
- [ ] 04 — Индексы: B-tree изнутри, составные, покрывающие, GIN/GiST/BRIN
- [ ] 05 — Планировщик: статистика, алгоритмы соединений, чтение EXPLAIN
- [ ] 06 — Транзакции и изоляция: аномалии, MVCC, SSI
- [ ] 07 — Блокировки: FOR UPDATE, SKIP LOCKED, advisory, дедлоки
- [ ] 08 — WAL, checkpoint, VACUUM, bloat, wraparound
- [ ] 09 — Python ↔ БД в проде: пулы, COPY, ретраи, миграции без даунтайма
- [ ] 10 — Масштабирование: репликация, партиционирование, шардирование, PITR
- [ ] **Capstone 1** — бэкенд заказов и платежей под конкурентной нагрузкой

### Часть II. OLAP — DuckDB, ClickHouse
- [ ] 11 — Колоночное хранение, компрессия, векторное исполнение
- [ ] 12 — Моделирование DWH: Kimball, SCD, Data Vault, medallion
- [ ] 13 — ClickHouse изнутри: MergeTree, гранулы, движки, MV, projections
- [ ] 14 — Аналитический SQL: когорты, retention, воронки, approx
- [ ] 15 — ETL/ELT и CDC: PostgreSQL → Kafka → ClickHouse
- [ ] 16 — Распределённый ClickHouse
- [ ] **Capstone 2** — DWH маркетплейса, дашборды < 1 с на 100M+ строк

### Часть III. NoSQL и распределённые системы
- [ ] 17 — Теория: CAP/PACELC, модели консистентности, кворумы, Raft
- [ ] 18 — Redis
- [ ] 19 — MongoDB
- [ ] 20 — Cassandra / ScyllaDB
- [ ] 21 — Storage engines: B-tree vs LSM (+ мини-LSM на Python)
- [ ] 22 — Архитектура данных: outbox, saga, CQRS, event sourcing, system design
- [ ] **Capstone 3** — system design + реализация

## Структура

```
docker-compose.yml   сервисы по профилям (oltp сейчас; olap/nosql/cdc — позже)
datasets/            генератор синтетического маркетплейса (детерминированный, COPY)
common/              подключения, запуск решений, сверка с эталоном
lessons/NN-*/        README.md — теория, tasks.md — задачи, sql/ и py/ — решения, tests/
notes/               твой конспект, ответы на вопросы, журнал ошибок
capstones/           сквозные проекты
```

## Основная литература

- Martin Kleppmann, *Designing Data-Intensive Applications* (2nd ed.) — сквозная книга курса
- Егор Рогов, [*PostgreSQL изнутри*](https://postgrespro.ru/education/books/internals) (бесплатно) — уроки 03–08
- Alex Petrov, *Database Internals* — уроки 03–04, 17, 20–21
- Ralph Kimball, *The Data Warehouse Toolkit* — урок 12
- CMU 15-445 / 15-721 (Andy Pavlo) — лекции на YouTube
