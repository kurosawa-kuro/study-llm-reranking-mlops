from __future__ import annotations

import csv
import json
import os
from datetime import date
from pathlib import Path

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from src.eval.offline_metrics import compute_offline_metrics
from src.infra.db import get_db_connection

REPORT_DIR = Path("/app/artifacts/reports")


def ensure_latest_offline_eval() -> dict:
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    evaluated_queries,
                    ndcg10_meili,
                    ndcg10_lgbm,
                    map_meili,
                    map_lgbm,
                    recall20_meili,
                    recall20_lgbm,
                    created_at
                FROM offline_eval_reports
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            row = cur.fetchone()

        if row is not None:
            return row

        metrics = compute_offline_metrics()
        with conn.cursor(row_factory=dict_row) as cur:
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
                RETURNING
                    id,
                    evaluated_queries,
                    ndcg10_meili,
                    ndcg10_lgbm,
                    map_meili,
                    map_lgbm,
                    recall20_meili,
                    recall20_lgbm,
                    created_at;
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
            created = cur.fetchone()
        conn.commit()
        return created


def load_weekly_kpi() -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    stat_date,
                    impressions,
                    clicks,
                    favorites,
                    inquiries,
                    ctr,
                    favorite_rate,
                    inquiry_rate,
                    cvr
                FROM kpi_daily_stats
                ORDER BY stat_date DESC
                LIMIT 7;
                """
            )
            rows = cur.fetchall()
    return list(reversed(rows))


def summarize_weekly_kpi(rows: list[dict]) -> dict[str, float | int]:
    if not rows:
        return {
            "days": 0,
            "impressions": 0,
            "clicks": 0,
            "favorites": 0,
            "inquiries": 0,
            "ctr": 0.0,
            "favorite_rate": 0.0,
            "inquiry_rate": 0.0,
            "cvr": 0.0,
        }

    impressions = sum(int(row["impressions"]) for row in rows)
    clicks = sum(int(row["clicks"]) for row in rows)
    favorites = sum(int(row["favorites"]) for row in rows)
    inquiries = sum(int(row["inquiries"]) for row in rows)

    ctr = (clicks / impressions) if impressions > 0 else 0.0
    favorite_rate = (favorites / impressions) if impressions > 0 else 0.0
    inquiry_rate = (inquiries / impressions) if impressions > 0 else 0.0
    cvr = (inquiries / clicks) if clicks > 0 else 0.0

    return {
        "days": len(rows),
        "impressions": impressions,
        "clicks": clicks,
        "favorites": favorites,
        "inquiries": inquiries,
        "ctr": round(ctr, 6),
        "favorite_rate": round(favorite_rate, 6),
        "inquiry_rate": round(inquiry_rate, 6),
        "cvr": round(cvr, 6),
    }


def evaluate_adoption(offline: dict, weekly_kpi: dict[str, float | int]) -> tuple[bool, str, dict[str, float | int]]:
    min_queries = int(os.getenv("PHASE6_MIN_EVAL_QUERIES", "10"))
    min_ndcg_gain = float(os.getenv("PHASE6_MIN_NDCG_GAIN", "0.02"))
    min_map_gain = float(os.getenv("PHASE6_MIN_MAP_GAIN", "0.01"))
    require_recall_non_decrease = os.getenv("PHASE6_REQUIRE_RECALL_NON_DECREASE", "true").lower() == "true"

    ndcg_gain = float(offline["ndcg10_lgbm"]) - float(offline["ndcg10_meili"])
    map_gain = float(offline["map_lgbm"]) - float(offline["map_meili"])
    recall_diff = float(offline["recall20_lgbm"]) - float(offline["recall20_meili"])

    reasons: list[str] = []

    if int(offline["evaluated_queries"]) < min_queries:
        reasons.append(f"insufficient_queries<{min_queries}")
    if ndcg_gain < min_ndcg_gain:
        reasons.append(f"ndcg_gain<{min_ndcg_gain}")
    if map_gain < min_map_gain:
        reasons.append(f"map_gain<{min_map_gain}")
    if require_recall_non_decrease and recall_diff < 0:
        reasons.append("recall_decreased")

    if int(weekly_kpi["impressions"]) == 0:
        reasons.append("no_online_impressions")

    adopt = len(reasons) == 0
    reason = "passed" if adopt else ",".join(reasons)

    thresholds = {
        "min_queries": min_queries,
        "min_ndcg_gain": min_ndcg_gain,
        "min_map_gain": min_map_gain,
        "require_recall_non_decrease": require_recall_non_decrease,
    }
    return adopt, reason, thresholds


def save_decision(adopt: bool, reason: str, thresholds: dict, metrics: dict) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_adoption_decisions (adopt_lgbm, reason, thresholds, metrics)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (adopt, reason, Jsonb(thresholds), Jsonb(metrics)),
            )
            decision_id = int(cur.fetchone()[0])
        conn.commit()
    return decision_id


def write_reports(offline: dict, weekly_rows: list[dict], weekly_summary: dict, adopt: bool, reason: str) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    csv_path = REPORT_DIR / f"phase6_weekly_eval_{today}.csv"
    md_path = REPORT_DIR / f"phase6_weekly_eval_{today}.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "key", "value"])

        for key in [
            "evaluated_queries",
            "ndcg10_meili",
            "ndcg10_lgbm",
            "map_meili",
            "map_lgbm",
            "recall20_meili",
            "recall20_lgbm",
        ]:
            writer.writerow(["offline_eval", key, offline[key]])

        for key in [
            "days",
            "impressions",
            "clicks",
            "favorites",
            "inquiries",
            "ctr",
            "favorite_rate",
            "inquiry_rate",
            "cvr",
        ]:
            writer.writerow(["weekly_kpi", key, weekly_summary[key]])

        writer.writerow(["decision", "adopt_lgbm", adopt])
        writer.writerow(["decision", "reason", reason])

    ndcg_gain = float(offline["ndcg10_lgbm"]) - float(offline["ndcg10_meili"])
    map_gain = float(offline["map_lgbm"]) - float(offline["map_meili"])
    recall_gain = float(offline["recall20_lgbm"]) - float(offline["recall20_meili"])

    lines = [
        "# Phase6 Weekly Evaluation Report",
        "",
        "## Offline Metrics",
        f"- evaluated_queries: {offline['evaluated_queries']}",
        f"- ndcg@10 (meili): {offline['ndcg10_meili']}",
        f"- ndcg@10 (lgbm): {offline['ndcg10_lgbm']}",
        f"- ndcg@10 gain: {ndcg_gain:.6f}",
        f"- MAP (meili): {offline['map_meili']}",
        f"- MAP (lgbm): {offline['map_lgbm']}",
        f"- MAP gain: {map_gain:.6f}",
        f"- Recall@20 (meili): {offline['recall20_meili']}",
        f"- Recall@20 (lgbm): {offline['recall20_lgbm']}",
        f"- Recall@20 diff: {recall_gain:.6f}",
        "",
        "## Weekly KPI Summary",
        f"- days: {weekly_summary['days']}",
        f"- impressions: {weekly_summary['impressions']}",
        f"- clicks: {weekly_summary['clicks']}",
        f"- favorites: {weekly_summary['favorites']}",
        f"- inquiries: {weekly_summary['inquiries']}",
        f"- ctr: {weekly_summary['ctr']}",
        f"- favorite_rate: {weekly_summary['favorite_rate']}",
        f"- inquiry_rate: {weekly_summary['inquiry_rate']}",
        f"- cvr: {weekly_summary['cvr']}",
        "",
        "## Daily KPI Rows (latest 7)",
    ]

    for row in weekly_rows:
        lines.append(
            f"- {row['stat_date']}: imp={row['impressions']} click={row['clicks']} "
            f"fav={row['favorites']} inq={row['inquiries']} ctr={row['ctr']} cvr={row['cvr']}"
        )

    lines.extend(
        [
            "",
            "## Adoption Decision",
            f"- adopt_lgbm: {adopt}",
            f"- reason: {reason}",
        ]
    )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path


def main() -> None:
    offline = ensure_latest_offline_eval()
    weekly_rows = load_weekly_kpi()
    weekly_summary = summarize_weekly_kpi(weekly_rows)

    adopt, reason, thresholds = evaluate_adoption(offline, weekly_summary)

    metrics = {
        "offline": {
            "evaluated_queries": int(offline["evaluated_queries"]),
            "ndcg10_meili": float(offline["ndcg10_meili"]),
            "ndcg10_lgbm": float(offline["ndcg10_lgbm"]),
            "map_meili": float(offline["map_meili"]),
            "map_lgbm": float(offline["map_lgbm"]),
            "recall20_meili": float(offline["recall20_meili"]),
            "recall20_lgbm": float(offline["recall20_lgbm"]),
        },
        "weekly_kpi": weekly_summary,
    }

    decision_id = save_decision(adopt, reason, thresholds, metrics)
    csv_path, md_path = write_reports(offline, weekly_rows, weekly_summary, adopt, reason)

    print(
        "Weekly evaluation report completed: "
        f"decision_id={decision_id}, adopt_lgbm={adopt}, reason={reason}, "
        f"csv={csv_path}, md={md_path}"
    )


if __name__ == "__main__":
    main()
