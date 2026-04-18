up:
	docker compose up -d

build:
	docker compose build api

down:
	docker compose down

logs:
	docker compose logs -f api postgres meilisearch pgadmin redis

health:
	curl -s http://localhost:8000/health

phase1-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/001_create_properties.sql

phase1-seed:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/002_seed_properties.sql

phase1-sync:
	docker compose exec -T api python -m src.batch.meili_sync

phase1-bootstrap: phase1-migrate phase1-seed phase1-sync

phase1-search-check:
	curl -sG "http://localhost:8000/search" \
		--data-urlencode "q=札幌" \
		--data-urlencode "layout=2LDK" \
		--data-urlencode "price_lte=90000" \
		--data-urlencode "pet=true"

phase2-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/003_create_logs_and_stats.sql

phase2-bootstrap: phase2-migrate

phase2-feedback-check:
	bash -lc 'for i in 1 2 3 4 5; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); SEARCH_LOG_ID=$$(printf "%s" "$$RESP" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"search_log_id\", \"\"))" 2>/dev/null || true); if [ -n "$$SEARCH_LOG_ID" ]; then curl -s -X POST "http://localhost:8000/feedback" -H "Content-Type: application/json" -d "{\"user_id\":1,\"property_id\":1,\"action\":\"click\",\"search_log_id\":$${SEARCH_LOG_ID}}"; exit 0; fi; sleep 2; done; echo "phase2-feedback-check failed: search_log_id not found"; exit 1'

phase3-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/004_phase3_features_and_batch_logs.sql

phase3-bootstrap: phase3-migrate

phase3-daily:
	docker compose exec -T api python -m src.batch.daily_stats

phase3-feature-check:
	docker compose exec -T api python -m src.batch.feature_report

phase4-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/005_phase4_me5.sql

phase4-generate-embeddings:
	docker compose exec -T api python -m src.batch.me5_generate

phase4-bootstrap: phase4-migrate phase4-generate-embeddings

phase4-daily:
	docker compose exec -T api python -m src.batch.daily_stats

phase4-feature-check:
	docker compose exec -T api python -m src.batch.feature_report

phase4-search-check:
	bash -lc 'RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌 ペット可 2LDK" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); printf "%s" "$$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); first=(d.get(\"items\") or [{}])[0]; print(\"search_log_id=\", d.get(\"search_log_id\")); print(\"first_item_id=\", first.get(\"id\")); print(\"first_item_me5_score=\", first.get(\"me5_score\"));"'

phase5-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/006_phase5_learning_logs.sql
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/007_phase5_ranking_compare_logs.sql

phase5-generate-train:
	docker compose exec -T api python -m src.ml.training_data

phase5-train:
	docker compose exec -T api python -m src.ml.train_lgbm

phase5-label-seed:
	bash -lc 'for action in click favorite inquiry; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); LOG_ID=$$(printf "%s" "$$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get(\"search_log_id\",\"\"))" 2>/dev/null || true); PID=$$(printf "%s" "$$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get(\"items\",[]); print(items[0].get(\"id\",\"\") if items else \"\")" 2>/dev/null || true); if [ -n "$$LOG_ID" ] && [ -n "$$PID" ]; then curl -s -X POST "http://localhost:8000/feedback" -H "Content-Type: application/json" -d "{\"user_id\":1,\"property_id\":$${PID},\"action\":\"$${action}\",\"search_log_id\":$${LOG_ID}}" > /dev/null; fi; done; echo "phase5-label-seed completed"'

phase5-bootstrap: phase5-migrate phase5-label-seed phase5-generate-train phase5-train

phase5-search-check:
	bash -lc 'for i in 1 2 3 4 5 6 7 8 9 10; do RESP=$$(curl -sG "http://localhost:8000/search" --data-urlencode "q=札幌" --data-urlencode "layout=2LDK" --data-urlencode "price_lte=90000" --data-urlencode "pet=true" --data-urlencode "user_id=1"); if printf "%s" "$$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); first=(d.get(\"items\") or [{}])[0]; print(\"search_log_id=\", d.get(\"search_log_id\")); print(\"first_item_id=\", first.get(\"id\")); print(\"first_item_lgbm_score=\", first.get(\"lgbm_score\")); print(\"first_item_me5_score=\", first.get(\"me5_score\"));" 2>/dev/null; then exit 0; fi; sleep 1; done; echo "phase5-search-check failed: API did not return valid JSON"; exit 1'

phase5-compare-check:
	docker compose exec -T api python -m src.batch.ranking_compare_report

phase6-migrate:
	docker compose exec -T api python -m src.batch.run_sql src/infra/migrations/008_phase6_eval_and_kpi.sql

phase6-offline-eval:
	docker compose exec -T api python -m src.batch.offline_eval

phase6-kpi-daily:
	docker compose exec -T api python -m src.batch.kpi_daily

phase6-weekly-report:
	docker compose exec -T api python -m src.batch.weekly_eval_report

phase6-weekly-retrain:
	docker compose exec -T api python -m src.batch.weekly_retrain

phase6-bootstrap: phase6-migrate phase6-kpi-daily phase6-offline-eval phase6-weekly-report

