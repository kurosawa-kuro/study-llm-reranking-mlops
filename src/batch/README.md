# Batch Module

責務ごとにサブフォルダを分けて管理する。

- `maintenance/`: SQL 実行や初期化補助
- `features/`: 日次特徴量更新と確認レポート
- `embeddings/`: ME5 埋め込み生成
- `search_index/`: 検索インデックス同期
- `evaluation/metrics/`: KPI 集計、オフライン評価、採用判定保存・参照
- `evaluation/reports/`: 比較ログ出力、週次評価レポート出力
- `training/`: 週次再学習の実行制御
