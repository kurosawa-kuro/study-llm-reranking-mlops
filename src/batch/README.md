# Batch Module

定期処理と運用用コマンドを責務ごとに分けて管理する。

## Structure

- `maintenance/`: SQL 実行や初期化補助
- `features/`: 日次特徴量更新と確認レポート
- `embeddings/`: ME5 埋め込み生成
- `search_index/`: 検索インデックス同期
- `evaluation/metrics/`: KPI 集計、オフライン評価、採用判定保存・参照
- `evaluation/reports/`: 比較ログ出力、週次評価レポート出力
- `training/`: 週次再学習の実行制御

## Design Rule

- `metrics` は数値計算や保存処理
- `reports` は CSV / Markdown などの出力処理
- `search_index` は検索基盤との同期だけを持つ
- `training` は採用判定を受けた後段の再学習実行を持つ

## Main Entry Points

- `maintenance.run_sql`
- `features.daily_stats`
- `features.feature_report`
- `embeddings.me5_generate`
- `search_index.meili_sync`
- `evaluation.metrics.kpi_daily`
- `evaluation.metrics.offline_eval`
- `evaluation.reports.ranking_compare_report`
- `evaluation.reports.weekly_eval_report`
- `training.weekly_retrain`

## Notes

- 実行面は `Makefile` の phase ターゲットに揃えている
- `python -m src.batch...` で直接起動できるように package 構成を保つ
