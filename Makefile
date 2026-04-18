.PHONY: \
	help up build down logs health \
	db-migrate-core db-seed-properties db-migrate-ops db-migrate-features db-migrate-embeddings db-migrate-learning db-migrate-eval \
	search-sync search-check feedback-check ranking-check ranking-check-verbose \
	features-daily features-report \
	embeddings-generate \
	training-label-seed training-generate training-fit \
	eval-compare eval-offline kpi-daily eval-weekly-report retrain-weekly \
	ops-bootstrap ops-daily ops-weekly verify-pipeline \
	phase1-migrate phase1-seed phase1-sync phase1-bootstrap phase1-search-check \
	phase2-migrate phase2-bootstrap phase2-feedback-check \
	phase3-migrate phase3-bootstrap phase3-daily phase3-feature-check \
	phase4-migrate phase4-generate-embeddings phase4-bootstrap phase4-daily phase4-feature-check phase4-search-check \
	phase5-migrate phase5-generate-train phase5-train phase5-label-seed phase5-bootstrap phase5-search-check phase5-compare-check \
	phase6-migrate phase6-offline-eval phase6-kpi-daily phase6-weekly-report phase6-weekly-retrain phase6-bootstrap

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
	&& echo "  Operations:" \
	&& echo "    make ops-bootstrap  # one-time setup (migrations + seed + index + model prep)" \
	&& echo "    make ops-daily      # daily sync/feature/embed/kpi tasks" \
	&& echo "    make ops-weekly     # weekly evaluate/report/retrain tasks" \
	&& echo "    make verify-pipeline # representative end-to-end checks"

up:
	docker compose up -d

build:
	docker compose build api

down:
	docker compose down

logs:
	docker compose logs -f api postgres meilisearch pgadmin redis

health:
	bash -lc 'for i in 1 2 3 4 5 6 7 8 9 10; do curl -fsS http://localhost:8000/health && exit 0; sleep 2; done; echo "health check failed"; exit 1'

db-migrate-core:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/001_create_properties.sql

db-seed-properties:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/002_seed_properties.sql

db-migrate-ops:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/003_create_logs_and_stats.sql

db-migrate-features:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/004_phase3_features_and_batch_logs.sql

db-migrate-embeddings:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/005_phase4_me5.sql

db-migrate-learning:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/006_phase5_learning_logs.sql
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/007_phase5_ranking_compare_logs.sql

db-migrate-eval:
	docker compose exec -T api python -m src.jobs.maintenance.run_migrations src/migrations/008_phase6_eval_and_kpi.sql

search-sync:
	docker compose exec -T api python -m src.jobs.indexing.sync_properties_to_meilisearch

search-check:
	curl -sG "http://localhost:8000/search" \
		--data-urlencode "q=札幌" \
		--data-urlencode "layout=2LDK" \
		--data-urlencode "price_lte=90000" \
		--data-urlencode "pet=true"

feedback-check:
	bash -lc 'for i in 1 2 3 4 5; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); SEARCH_LOG_ID=$$(printf "%s" "$$RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"search_log_id\", \"\"))" 2>/dev/null || true); if [ -n "$$SEARCH_LOG_ID" ]; then curl -s -X POST "http://localhost:8000/feedback" -H "Content-Type: application/json" -d "{\"user_id\":1,\"property_id\":1,\"action\":\"click\",\"search_log_id\":$${SEARCH_LOG_ID}}"; exit 0; fi; sleep 2; done; echo "phase2-feedback-check failed: search_log_id not found"; exit 1'

features-daily:
	docker compose exec -T api python -m src.jobs.features.aggregate_daily_property_stats

features-report:
	docker compose exec -T api python -m src.jobs.features.export_feature_report

embeddings-generate:
	docker compose exec -T api python -m src.jobs.embeddings.generate_property_embeddings

ranking-check:
	bash -lc 'RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌 ペット可 2LDK" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); printf "%s" "$$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); first=(d.get(\"items\") or [{}])[0]; print(\"search_log_id=\", d.get(\"search_log_id\")); print(\"first_item_id=\", first.get(\"id\")); print(\"first_item_me5_score=\", first.get(\"me5_score\"));"'

training-generate:
	docker compose exec -T api python -m src.trainers.training_dataset_builder

training-fit:
	docker compose exec -T api python -m src.trainers.lgbm_trainer

training-label-seed:
	bash -lc 'for action in click favorite inquiry; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); LOG_ID=$$(printf "%s" "$$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"search_log_id\",\"\"))" 2>/dev/null || true); PID=$$(printf "%s" "$$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get(\"items\",[]); print(items[0].get(\"id\",\"\") if items else \"\")" 2>/dev/null || true); if [ -n "$$LOG_ID" ] && [ -n "$$PID" ]; then curl -s -X POST "http://localhost:8000/feedback" -H "Content-Type: application/json" -d "{\"user_id\":1,\"property_id\":$${PID},\"action\":\"$${action}\",\"search_log_id\":$${LOG_ID}}" > /dev/null; fi; done; echo "phase5-label-seed completed"'

ranking-check-verbose:
	bash -lc 'for i in 1 2 3 4 5 6 7 8 9 10; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); if printf "%s" "$$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); first=(d.get(\"items\") or [{}])[0]; print(\"search_log_id=\", d.get(\"search_log_id\")); print(\"first_item_id=\", first.get(\"id\")); print(\"first_item_lgbm_score=\", first.get(\"lgbm_score\")); print(\"first_item_me5_score=\", first.get(\"me5_score\"));" 2>/dev/null; then exit 0; fi; sleep 1; done; echo "phase5-search-check failed: API did not return valid JSON"; exit 1'

eval-compare:
	docker compose exec -T api python -m src.jobs.evaluation.export_ranking_compare_report

eval-offline:
	docker compose exec -T api python -m src.jobs.evaluation.run_offline_evaluation

kpi-daily:
	docker compose exec -T api python -m src.jobs.evaluation.aggregate_daily_kpi

eval-weekly-report:
	docker compose exec -T api python -m src.jobs.evaluation.export_weekly_evaluation_report

retrain-weekly:
	docker compose exec -T api python -m src.jobs.training.run_weekly_retraining

ops-bootstrap: db-migrate-core db-seed-properties db-migrate-ops db-migrate-features db-migrate-embeddings db-migrate-learning db-migrate-eval search-sync embeddings-generate training-label-seed training-generate training-fit

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
	$(MAKE) health
	$(MAKE) search-check
	$(MAKE) feedback-check
	$(MAKE) ranking-check
	$(MAKE) ranking-check-verbose
	$(MAKE) eval-compare
	$(MAKE) eval-offline

# Backward-compatible aliases (deprecated)
phase1-migrate: db-migrate-core
phase1-seed: db-seed-properties
phase1-sync: search-sync
phase1-bootstrap: db-migrate-core db-seed-properties search-sync
phase1-search-check: search-check

phase2-migrate: db-migrate-ops
phase2-bootstrap: db-migrate-ops
phase2-feedback-check: feedback-check

phase3-migrate: db-migrate-features
phase3-bootstrap: db-migrate-features
phase3-daily: features-daily
phase3-feature-check: features-report

phase4-migrate: db-migrate-embeddings
phase4-generate-embeddings: embeddings-generate
phase4-bootstrap: db-migrate-embeddings embeddings-generate
phase4-daily: features-daily
phase4-feature-check: features-report
phase4-search-check: ranking-check

phase5-migrate: db-migrate-learning
phase5-generate-train: training-generate
phase5-train: training-fit
phase5-label-seed: training-label-seed
phase5-bootstrap: db-migrate-learning training-label-seed training-generate training-fit
phase5-search-check: ranking-check-verbose
phase5-compare-check: eval-compare

phase6-migrate: db-migrate-eval
phase6-offline-eval: eval-offline
phase6-kpi-daily: kpi-daily
phase6-weekly-report: eval-weekly-report
phase6-weekly-retrain: retrain-weekly
phase6-bootstrap: db-migrate-eval kpi-daily eval-offline eval-weekly-report

