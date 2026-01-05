import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

import psycopg

ROOT_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT_DIR / "docs" / "schema.sql"


def get_dsn() -> str:
    dsn = os.getenv("PG_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("PG_DSN or DATABASE_URL must be set")
    return dsn


def get_conn():
    return psycopg.connect(get_dsn())


def run_schema():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Schema applied")


def upsert_jobs(jobs: Iterable[Dict[str, Any]]):
    rows = [
        (
            job.get("id"),
            job.get("source_id"),
            job.get("source_job_id"),
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("employment_type"),
            job.get("seniority"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("currency"),
            job.get("is_remote", False),
            job.get("url"),
            job.get("description"),
            job.get("tags"),
            job.get("published_at"),
        )
        for job in jobs
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO jobs (
                    id, source_id, source_job_id, title, company, location,
                    employment_type, seniority, salary_min, salary_max, currency,
                    is_remote, url, description, tags, published_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    source_id = EXCLUDED.source_id,
                    source_job_id = EXCLUDED.source_job_id,
                    title = EXCLUDED.title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    employment_type = EXCLUDED.employment_type,
                    seniority = EXCLUDED.seniority,
                    salary_min = EXCLUDED.salary_min,
                    salary_max = EXCLUDED.salary_max,
                    currency = EXCLUDED.currency,
                    is_remote = EXCLUDED.is_remote,
                    url = EXCLUDED.url,
                    description = EXCLUDED.description,
                    tags = EXCLUDED.tags,
                    published_at = EXCLUDED.published_at
                """,
                rows,
            )
        conn.commit()
    print(f"Upserted {len(rows)} jobs")


def fetch_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT * FROM jobs ORDER BY ingested_at DESC LIMIT %s", (limit,))
            return list(cur.fetchall())


def seed_from_file(path: Path):
    jobs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(jobs, list):
        raise SystemExit("Seed file must be a JSON list")
    upsert_jobs(jobs)


def main():
    parser = argparse.ArgumentParser(description="Postgres helpers")
    parser.add_argument("--init-schema", action="store_true", help="Apply schema.sql to the database")
    parser.add_argument("--seed", type=Path, help="Seed jobs from JSON file")
    parser.add_argument("--list", action="store_true", help="List jobs (debug)")
    args = parser.parse_args()

    if args.init_schema:
        run_schema()
    if args.seed:
        seed_from_file(args.seed)
    if args.list:
        jobs = fetch_jobs()
        print(json.dumps(jobs, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
