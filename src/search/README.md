# Search Module

検索条件の組み立て、Meilisearch への問い合わせ、ME5 類似度付与、LightGBM 再ランキングの入口を持つモジュール。

## Responsibilities

- `query_builder.py`: API パラメータから Meilisearch の検索 payload を組み立てる
- `meili_client.py`: Meilisearch HTTP API の薄いクライアント
- `search_service.py`: 検索実行、ME5 スコア付与、LightGBM 再ランキング、検索ログ保存をまとめる

## Main Flow

1. `build_search_payload()` が `city`, `layout`, `price_lte`, `pet`, `walk_min` から filter を構築する
2. `MeiliClient.search()` で候補物件を取得する
3. `attach_me5_scores()` がクエリ embedding と物件 embedding の cosine similarity を計算する
4. `rerank_with_lgbm()` が `property_features` と `me5_score` を使って再ランキングする
5. `safe_log_ranked_search()` が `search_logs` と `ranking_compare_logs` を更新する

## Inputs And Dependencies

- `src.api.routes.search` から呼ばれる
- `src.infra.repositories.engagement` で検索ログと impression を記録する
- `src.infra.repositories.me5_repository` から物件 embedding を読む
- `src.infra.repositories.ranking_compare` へ Meili 順位と rerank 順位の差分を保存する
- `src.ml.me5_embed` と `src.ml.similarity` を使って ME5 類似度を算出する
- `src.ranking.inference` で LightGBM 推論を行う

## Notes

- 空クエリ時は `me5_score=0.0` を入れてパイプラインを維持する
- Meilisearch の index 名はデフォルトで `properties`
- API 障害時の HTTP エラー処理は `src.api.routes.search` 側で行う
