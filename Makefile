PY?=/Users/user/Documents/code/job-tinder/.venv/bin/python
PIP?=/Users/user/Documents/code/job-tinder/.venv/bin/pip
COMPOSE?=docker compose
PG_DSN?=postgres://jobtinder:jobtinder@localhost:5432/job_tinder

.PHONY: install test api pg-up pg-down pg-logs pg-init pg-seed pg-list api-pg

install:
	$(PIP) install -r backend/requirements.txt

test:
	$(PY) -m pytest backend/tests

api:
	./scripts/dev_api.sh

api-pg:
	STORE=pg PG_DSN=$(PG_DSN) ./scripts/dev_api.sh

pg-up:
	$(COMPOSE) up -d postgres

pg-down:
	$(COMPOSE) down

pg-logs:
	$(COMPOSE) logs -f postgres

pg-init:
	PG_DSN=$(PG_DSN) $(PY) -m backend.db.pg --init-schema

pg-seed:
	PG_DSN=$(PG_DSN) $(PY) -m backend.db.pg --seed data/sample_jobs.json

pg-list:
	PG_DSN=$(PG_DSN) $(PY) -m backend.db.pg --list
