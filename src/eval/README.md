# Eval Module

検索品質をオフラインで評価するモジュール。現在は `ranking_compare_logs` と `search_logs` を使って、Meili と LightGBM rerank の差を集計する。

## Responsibilities

- `offline_metrics.py`: NDCG@10、MAP、Recall@20 を計算する

## Data Source

- `ranking_compare_logs.meili_result_ids`
- `ranking_compare_logs.reranked_result_ids`
- `search_logs.actioned_id`
- `search_logs.action_type`

## Current Metrics

- `ndcg10_meili`
- `ndcg10_lgbm`
- `map_meili`
- `map_lgbm`
- `recall20_meili`
- `recall20_lgbm`
- `evaluated_queries`

## Used By

- `src.batch.evaluation.metrics.offline_eval`
- `src.batch.evaluation.reports.weekly_eval_report`

## Notes

- 対象は `click`, `favorite`, `inquiry` の action が付いた検索ログのみ
- gain は `click=1`, `favorite=2`, `inquiry=3` として扱う
