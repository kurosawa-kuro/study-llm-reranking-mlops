# Infra Module

外部システムや永続化層との接続をまとめるモジュール。ビジネスロジックから SQL とストレージ操作を分離する役割を持つ。

## Responsibilities

- `db.py`: PostgreSQL 接続生成
- `engagement.py`: `search_logs` と `property_stats` の更新
- `me5_repository.py`: 物件 embedding の保存・取得
- `ranking_compare.py`: Meili 結果と rerank 結果の比較ログ保存

## Used By

- `src.api.routes.feedback`
- `src.search.search_service`
- `src.batch.*`
- `src.eval.offline_metrics`
- `src.ml.training_data`

## Notes

- DB 接続は `POSTGRES_PASSWORD` を必須にしている
- その他の接続先は `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` で上書きできる
- 低レイヤでは例外を握りつぶさず、呼び出し側で制御する前提
