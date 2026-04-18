# study-llm-reranking-mlops

不動産検索ランキング基盤の学習用リポジトリです。

## Phase 0 実装済み範囲

- FastAPI の最小 API（health エンドポイント）
- Docker Compose によるローカル起動基盤
- PostgreSQL / pgAdmin / Meilisearch / Redis の連携雛形
- 初期ディレクトリ構成（api/search/ranking/ml/batch/infra）

## Phase 1 実装済み範囲

- `properties` テーブル作成 SQL
- seed データ投入 SQL
- PostgreSQL から Meilisearch への同期バッチ
- `GET /search` 実装（絞り込み対応）

## Phase 2 実装済み範囲

- `search_logs` / `property_stats` テーブル作成 SQL
- 検索時ログ保存（query, user_id, result_ids）
- impression 自動加算
- `POST /feedback` 実装（click/favorite/inquiry）
- click 時の `search_logs.clicked_id` 更新

## Phase 3 実装済み範囲

- `property_features` テーブル作成 SQL
- `batch_job_logs` テーブル作成 SQL
- 日次バッチ（CTR/Fav/Inq再集計、特徴量更新、inactive除外）
- バッチ実行結果ログ保存（success/failed, processed_count）
- 特徴量レポート出力

## Phase 4 実装済み範囲

- `property_embeddings` テーブル作成 SQL
- `search_logs.me5_scores` カラム追加
- `property_features.me5_score` カラム追加
- 物件埋め込み生成バッチ（ME5、オフライン時はdeterministic fallback）
- `GET /search` でME5類似度計算と再ランキング
- 日次特徴量更新で `me5_score` 集計反映

## Phase 5 着手済み範囲

- 学習ログ拡張（`search_logs.actioned_id`, `search_logs.action_type`）
- 学習データ生成スクリプト（`src/ml/training_data.py`）
- LightGBM 学習スクリプト（`src/ml/train_lgbm.py`）
- `GET /search` への LightGBM 推論再ランキング統合（モデル未学習時はfallback）
- Meili順と再ランキング順の比較ログ出力（`ranking_compare_logs`）

## Phase 6 実装済み範囲

- オフライン評価（NDCG@10, MAP, Recall@20）
- オンライン KPI 日次集計（CTR, favorite_rate, inquiry_rate, CVR）
- 週次レポート出力（CSV/Markdown）
- モデル採用判定ルール（閾値ベース）

## 起動

1. 依存コンテナを起動

	docker compose up -d

2. health チェック

	curl http://localhost:8000/health

3. Phase 1 初期データ投入

	make build
	make up
	make phase1-bootstrap

4. 検索確認

	make phase1-search-check

5. Phase 2 初期化と動作確認

	make phase2-bootstrap
	make phase2-feedback-check

6. Phase 3 初期化と日次バッチ確認

	make phase3-bootstrap
	make phase3-daily
	make phase3-feature-check

7. Phase 4 初期化とME5確認

	make phase4-bootstrap
	make phase4-search-check
	make phase4-daily
	make phase4-feature-check

8. Phase 5 学習と推論確認

	make phase5-migrate
	# 札幌 2LDK の実ヒット条件で click/favorite/inquiry を生成
	make phase5-label-seed
	make phase5-generate-train
	make phase5-train
	make phase5-search-check
	make phase5-compare-check

9. Phase 6 評価運用

	make phase6-migrate
	make phase6-kpi-daily
	make phase6-offline-eval
	make phase6-weekly-report

## アクセス先

- FastAPI: http://localhost:8000
- pgAdmin: http://localhost:5050
- Meilisearch: http://localhost:7700
- PostgreSQL: localhost:5432

## 主要ファイル

- docker-compose: ./docker-compose.yml
- FastAPI entrypoint: ./src/api/main.py
- environment template: ./.env.example

