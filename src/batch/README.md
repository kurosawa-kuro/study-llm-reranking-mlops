# Batch Module

責務ごとにサブフォルダを分けて管理する。

- `maintenance/`: SQL 実行や初期化補助
- `features/`: 日次特徴量更新と確認レポート
- `embeddings/`: Meilisearch 同期と ME5 埋め込み生成
- `evaluation/`: KPI 集計、比較ログ、オフライン評価、採用判定保存
- `training/`: 週次再学習の実行制御
