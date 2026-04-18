# ML Module

埋め込み生成、類似度計算、学習データ生成、LightGBM 学習を担当するモジュール。

## Responsibilities

- `me5_embed.py`: クエリ・物件テキストの embedding を生成する
- `similarity.py`: ベクトル類似度計算を提供する
- `training_data.py`: `search_logs` などから学習用 CSV を作る
- `train_lgbm.py`: LambdaRank で LightGBM モデルを学習し、成果物を保存する

## Runtime Behavior

- `sentence-transformers` が使える場合は実モデルを使用する
- 使えない場合でも `fallback_embedding()` により決定的な疑似 embedding を返す
- これにより、オフライン環境や依存不足でも一通りの検証が止まらない

## Artifacts

- 学習データ: `/app/artifacts/train/rank_train.csv`
- 学習済みモデル: `/app/artifacts/models/lgbm_ranker.txt`
- 学習メタデータ: `/app/artifacts/models/lgbm_ranker_metadata.json`

## Batch Entry Points

- `src.batch.embeddings.me5_generate`
- `src.batch.training.weekly_retrain`
- Phase 5 系の学習バッチ群
