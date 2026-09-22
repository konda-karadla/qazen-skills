"""Apply 002_runs_passthrough_metadata.sql and backfill base_url from S6."""
from __future__ import annotations

from pathlib import Path

import psycopg

URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "infra" / "sql" / "002_runs_passthrough_metadata.sql").read_text(encoding="utf-8")


def main() -> None:
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(SQL)
        cols = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'runs'
              AND column_name IN ('base_url', 'environment', 'branch')
            ORDER BY 1
            """
        ).fetchall()
        print("columns:", [r[0] for r in cols])

        updated = conn.execute(
            """
            UPDATE runs AS r
            SET base_url = sub.app_build
            FROM (
              SELECT a.run_id,
                     a.content->'environment_metadata'->>'app_build' AS app_build
              FROM artifacts a
              WHERE a.type = 's6_execution_result'
                AND a.content->'environment_metadata'->>'app_build' IS NOT NULL
                AND a.version = (
                  SELECT MAX(a2.version)
                  FROM artifacts a2
                  WHERE a2.run_id = a.run_id AND a2.type = 's6_execution_result'
                )
            ) AS sub
            WHERE r.run_id = sub.run_id
              AND (r.base_url IS NULL OR r.base_url = '')
            RETURNING r.run_id, r.base_url
            """
        ).fetchall()
        print("backfilled:", [(str(u[0]), u[1]) for u in updated])

        # Known Session 20/21 runs that had New Run base_url but may lack S6
        for rid, url in (
            ("fc8083f6-d524-4c48-aff6-f893075c8151", "http://127.0.0.1:8765"),
            ("b902b92f-6329-4af8-82d6-2faefe421845", "http://127.0.0.1:8765"),
        ):
            conn.execute(
                """
                UPDATE runs
                SET base_url = COALESCE(NULLIF(base_url, ''), %s),
                    environment = COALESCE(NULLIF(environment, ''), 'test')
                WHERE run_id = %s
                """,
                (url, rid),
            )
        check = conn.execute(
            "SELECT run_id, base_url, environment, branch FROM runs WHERE run_id = %s",
            ("fc8083f6-d524-4c48-aff6-f893075c8151",),
        ).fetchone()
        print("fc8083f6:", check)


if __name__ == "__main__":
    main()
