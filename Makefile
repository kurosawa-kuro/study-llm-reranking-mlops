.DEFAULT_GOAL := help

PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard ../.venv/bin/python),../.venv/bin/python,python3))

# docker compose を直接呼ばず、env/secret/credential.yaml を読み込むラッパー経由で起動する
DOCKER_COMPOSE ?= ./scripts/compose.sh

.PHONY: \
	help up build down logs health test dev-install api-refresh \
	check-layers \
	db-migrate-core db-seed-properties db-migrate-ops db-migrate-features db-migrate-embeddings db-migrate-learning db-migrate-eval \
	search-sync search-check feedback-check ranking-check ranking-check-verbose \
	features-daily features-report \
	embeddings-generate \
	training-label-seed training-generate training-fit training-fit-safe \
	eval-compare eval-offline kpi-daily eval-weekly-report retrain-weekly \
	ops-bootstrap ops-daily ops-weekly verify-pipeline

help:
	@echo "Available targets:" \
	&& echo "  Core:" \
	&& echo "    make up|build|down|logs|health" \
	&& echo "  Domain targets:" \
	&& echo "    make db-migrate-core db-seed-properties" \
	&& echo "    make search-sync search-check feedback-check" \
	&& echo "    make features-daily features-report embeddings-generate" \
	&& echo "    make training-label-seed training-generate training-fit" \
	&& echo "    make eval-offline kpi-daily eval-weekly-report retrain-weekly" \
	&& echo "    make dev-install    # install runtime and dev dependencies into .venv if present" \
	&& echo "    make test           # run local pytest in the active Python environment" \
	&& echo "    make check-layers   # enforce layer boundaries by AST (stage=5)" \
	&& echo "    make api-refresh    # rebuild and recreate only the api service" \
	&& echo "  Operations:" \
	&& echo "    make ops-bootstrap  # one-time setup (migrations + seed + index + model prep)" \
	&& echo "    make ops-daily      # daily sync/feature/embed/kpi tasks" \
	&& echo "    make ops-weekly     # weekly evaluate/report/retrain tasks" \
	&& echo "    make verify-pipeline # representative end-to-end checks"

up:
	$(DOCKER_COMPOSE) up -d

build:
	$(DOCKER_COMPOSE) build api

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f api postgres meilisearch pgadmin redis

health:
	$(PYTHON) scripts/ops/health_check.py

dev-install:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests/ -v

check-layers:
	$(PYTHON) scripts/check_layers.py --stage 5

api-refresh:
	$(DOCKER_COMPOSE) build api
	$(DOCKER_COMPOSE) up -d --force-recreate api

db-migrate-core:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/001_create_properties.sql

db-seed-properties:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/002_seed_properties.sql

db-migrate-ops:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/003_create_logs_and_stats.sql

db-migrate-features:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/004_features_and_batch_logs.sql

db-migrate-embeddings:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/005_me5.sql

db-migrate-learning:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/006_learning_logs.sql
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/007_ranking_compare_logs.sql

db-migrate-eval:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/008_eval_and_kpi.sql

search-sync:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.indexing.sync_properties_to_meilisearch

search-check:
	$(PYTHON) scripts/ops/search_check.py

feedback-check:
	$(PYTHON) scripts/ops/feedback_check.py

features-daily:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.features.aggregate_daily_property_stats

features-report:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.features.export_feature_report

embeddings-generate:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.embeddings.generate_property_embeddings

ranking-check:
	$(PYTHON) scripts/ops/ranking_check.py

training-generate:
	$(DOCKER_COMPOSE) exec -T api python -m src.trainers.training_dataset_builder

training-fit:
	$(DOCKER_COMPOSE) exec -T api python -m src.trainers.lgbm_trainer

training-fit-safe:
	$(PYTHON) scripts/ops/training_fit_safe.py

training-label-seed:
	$(PYTHON) scripts/ops/training_label_seed.py

ranking-check-verbose:
	$(PYTHON) scripts/ops/ranking_check_verbose.py

eval-compare:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.evaluation.export_ranking_compare_report

eval-offline:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.evaluation.run_offline_evaluation

kpi-daily:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.evaluation.aggregate_daily_kpi

eval-weekly-report:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.evaluation.export_weekly_evaluation_report

retrain-weekly:
	$(DOCKER_COMPOSE) exec -T api python -m src.jobs.training.run_weekly_retraining

ops-bootstrap: db-migrate-core db-seed-properties db-migrate-ops db-migrate-features db-migrate-embeddings db-migrate-learning db-migrate-eval search-sync embeddings-generate training-label-seed training-generate training-fit-safe

ops-daily:
	$(MAKE) search-sync
	$(MAKE) features-daily
	$(MAKE) embeddings-generate
	$(MAKE) kpi-daily

ops-weekly:
	$(MAKE) eval-compare
	$(MAKE) eval-offline
	$(MAKE) eval-weekly-report
	$(MAKE) retrain-weekly

verify-pipeline:
	$(MAKE) check-layers
	$(MAKE) health
	$(MAKE) search-check
	$(MAKE) feedback-check
	$(MAKE) ranking-check
	$(MAKE) ranking-check-verbose
	$(MAKE) eval-compare
	$(MAKE) eval-offline

