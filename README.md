# study-llm-reranking-mlops

不動産検索ランキング基盤の学習用リポジトリです。

## Phase 0 実装済み範囲

- FastAPI の最小 API（health エンドポイント）
- Docker Compose によるローカル起動基盤
- PostgreSQL / pgAdmin / Meilisearch / Redis の連携雛形
- 初期ディレクトリ構成（現在は責務別に `api/clients/services/trainers/jobs/core/repositories` へ整理）

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
- 学習データ生成スクリプト（`src/trainers/training_dataset_builder.py`）
- LightGBM 学習スクリプト（`src/trainers/lgbm_trainer.py`）
- `GET /search` への LightGBM 推論再ランキング統合（モデル未学習時はfallback）
- Meili順と再ランキング順の比較ログ出力（`ranking_compare_logs`）

## Phase 6 実装済み範囲

- オフライン評価（NDCG@10, MAP, Recall@20）
- オンライン KPI 日次集計（CTR, favorite_rate, inquiry_rate, CVR）
- 週次レポート出力（CSV/Markdown）
- モデル採用判定ルール（閾値ベース）
- `GET /search` の Redis キャッシュ（`SEARCH_CACHE_TTL_SECONDS`、既定 120 秒）

## テスト

- `tests/api/test_api.py`（`/health`, `/search`, `/feedback` の正常系）
- `tests/clients/test_redis_client.py`（キャッシュキー、hit/miss、障害時フォールバック）
- `tests/services/...`（検索・埋め込み・評価ロジック）
- 実行コマンド: `python3 -m pytest tests/ -v`

## 起動

1. コンテナ起動

	make build
	make up

2. ヘルスチェック

	make health

3. 初期セットアップ（一括）

	make ops-bootstrap

4. 基本動作確認

	make search-check
	make feedback-check
	make ranking-check

5. 定常運用

	make ops-daily
	make ops-weekly

6. 代表 E2E 確認

	make verify-pipeline

補足:

- 新規運用は責務ベースターゲット（`search-sync`, `features-daily`, `training-fit` など）を使用
- `phase*` ターゲットは後方互換 alias としてのみ残置

## アクセス先

- FastAPI: http://localhost:8000
- pgAdmin: http://localhost:5050
- Meilisearch: http://localhost:7700
- PostgreSQL: localhost:5432

## 主要ファイル

- docker-compose: ./docker-compose.yml
- FastAPI entrypoint: ./src/api/main.py
- environment template: ./.env.example

