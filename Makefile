-include .env
export

PG_PORT ?= 55432
PG_USER ?= student
PG_PASSWORD ?= student
PG_DB ?= shop
PG_TEST_DB ?= shop_test
SCALE ?= small
L ?= 01

PSQL_URL = postgresql://$(PG_USER):$(PG_PASSWORD)@localhost:$(PG_PORT)

.PHONY: install up-oltp down reset-oltp psql psql-test seed seed-test test status

PY = uv run python

install:            ## создать .venv и поставить зависимости (uv.lock фиксирует версии)
	uv sync

up-oltp:            ## поднять PostgreSQL
	docker compose --profile oltp up -d --wait

down:               ## остановить все сервисы (данные сохраняются)
	docker compose --profile '*' down

reset-oltp:         ## удалить кластер PG вместе с данными
	docker compose --profile oltp down -v

psql:               ## консоль к учебной БД
	psql $(PSQL_URL)/$(PG_DB)

psql-test:          ## консоль к тестовой БД (маленький детерминированный датасет)
	psql $(PSQL_URL)/$(PG_TEST_DB)

seed:               ## залить данные: make seed SCALE=tiny|small|medium|large
	$(PY) -m datasets.generator --scale $(SCALE) --db $(PG_DB)

seed-test:          ## залить детерминированный датасет для автотестов
	$(PY) -m datasets.generator --scale tiny --db $(PG_TEST_DB)

test:               ## проверить решения урока: make test L=01
	$(PY) -m pytest lessons/$(L)-*/tests

status:             ## размеры таблиц
	psql $(PSQL_URL)/$(PG_DB) -c "SELECT relname, n_live_tup, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
