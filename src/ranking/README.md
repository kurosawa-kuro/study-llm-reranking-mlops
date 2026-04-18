# Ranking Module

再ランキングに使う特徴量整形と LightGBM 推論を担当するモジュール。

## Responsibilities

- `features.py`: `property_stats` と `search_logs` から `property_features` を再計算する
- `inference.py`: 物件ごとの特徴量を集めて LightGBM で再スコアリングする

## Main Flow

- 日次バッチでは `src.batch.features.daily_stats` から `features.py` を呼び出して `property_features` を更新する
- 検索 API では `src.search.search_service` から `inference.py` を呼び出して結果順序を入れ替える

## Feature Set

現在の推論列は以下。

- `price`
- `walk_min`
- `age`
- `area`
- `ctr`
- `fav_rate`
- `inquiry_rate`
- `me5_score`

## Notes

- モデルファイルは `LGBM_MODEL_PATH` または `/app/artifacts/models/lgbm_ranker.txt` を参照する
- モデルが無い場合でも fallback score で再ランキングを継続する
- モデルファイルの更新時刻を見て自動再ロードするため、API 再起動なしで差し替えできる
