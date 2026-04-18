from __future__ import annotations

from src.eval.offline_metrics import compute_offline_metrics
from src.infra.db import get_db_connection


def save_report(metrics: dict[str, float | int]) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO offline_eval_reports (
                    evaluated_queries,
                    ndcg10_meili,
                    ndcg10_lgbm,
                    map_meili,
                    map_lgbm,
                    recall20_meili,
                    recall20_lgbm
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    int(metrics["evaluated_queries"]),
                    float(metrics["ndcg10_meili"]),
                    float(metrics["ndcg10_lgbm"]),
                    float(metrics["map_meili"]),
                    float(metrics["map_lgbm"]),
                    float(metrics["recall20_meili"]),
                    float(metrics["recall20_lgbm"]),
                ),
            )
            report_id = int(cur.fetchone()[0])
        conn.commit()
    return report_id


def main() -> None:
    metrics = compute_offline_metrics()
    report_id = save_report(metrics)

    print(
        "Offline eval completed: "
        f"report_id={report_id}, queries={metrics['evaluated_queries']}, "
        f"ndcg10(meili={metrics['ndcg10_meili']}, lgbm={metrics['ndcg10_lgbm']}), "
        f"map(meili={metrics['map_meili']}, lgbm={metrics['map_lgbm']}), "
        f"recall20(meili={metrics['recall20_meili']}, lgbm={metrics['recall20_lgbm']})"
    )


if __name__ == "__main__":
    main()
