import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import psycopg
from psycopg.rows import dict_row

from .helpers import job_matches

DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000000")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_dsn() -> str:
    dsn = os.getenv("PG_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("PG_DSN or DATABASE_URL must be set for STORE=pg")
    return dsn


def ensure_user(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (DEFAULT_USER_ID, "cli@example.com", "CLI User"),
        )
    conn.commit()


class PgStore:
    def __init__(self):
        root_env = os.getenv("JOB_TINDER_ROOT")
        self.root = Path(root_env) if root_env else Path(__file__).resolve().parents[2]
        self.sample_file = self.root / "data" / "sample_jobs.json"
        self.dsn = get_dsn()

    def conn(self):
        return psycopg.connect(self.dsn)

    def list_jobs(self, *, status: str, query: str | None, company: str | None, tags: List[str], remote: str, emp_type: str | None) -> List[Dict[str, Any]]:
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor(row_factory=dict_row) as cur:
                sql = """
                    SELECT j.*, COALESCE(s.decision, 'pending') AS decision, s.decided_at
                    FROM jobs j
                    LEFT JOIN swipes s ON s.job_id = j.id AND s.user_id = %(user_id)s
                    WHERE 1=1
                """
                params = {"user_id": DEFAULT_USER_ID}

                # Filter by status
                if status != "all":
                    if status == "pending":
                        sql += " AND s.decision IS NULL"
                    else:
                        sql += " AND s.decision = %(status)s"
                        params["status"] = status

                # Filter by query (title or description)
                if query:
                    sql += " AND (j.title ILIKE %(query)s OR j.description ILIKE %(query)s OR j.company ILIKE %(query)s)"
                    params["query"] = f"%{query}%"

                # Filter by company
                if company:
                    sql += " AND j.company ILIKE %(company)s"
                    params["company"] = f"%{company}%"

                # Filter by tags (overlap)
                if tags:
                    sql += " AND j.tags && %(tags)s"
                    params["tags"] = tags

                # Filter by remote
                if remote == "true":
                    sql += " AND j.is_remote = TRUE"
                elif remote == "false":
                    sql += " AND j.is_remote = FALSE"

                # Filter by employment type
                if emp_type:
                    sql += " AND j.employment_type ILIKE %(emp_type)s"
                    params["emp_type"] = f"%{emp_type}%"

                sql += " ORDER BY j.ingested_at DESC"

                cur.execute(sql, params)
                return list(cur.fetchall())

    def get_job(self, job_id: str) -> Dict[str, Any]:
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT j.*, COALESCE(s.decision, 'pending') AS decision, s.decided_at
                    FROM jobs j
                    LEFT JOIN swipes s ON s.job_id = j.id AND s.user_id = %s
                    WHERE j.id = %s
                    """,
                    (DEFAULT_USER_ID, job_id),
                )
                row = cur.fetchone()
                if not row:
                    raise KeyError("job_not_found")
                return row

    def swipe(self, job_id: str, decision: str):
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM jobs WHERE id = %s", (job_id,))
                if cur.fetchone() is None:
                    raise KeyError("job_not_found")
                cur.execute(
                    """
                    INSERT INTO swipes (id, user_id, job_id, decision, decided_at)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s)
                    ON CONFLICT (user_id, job_id) DO UPDATE SET
                        decision = EXCLUDED.decision,
                        decided_at = EXCLUDED.decided_at
                    """,
                    (DEFAULT_USER_ID, job_id, decision, utc_now()),
                )
            conn.commit()
        return {"job_id": job_id, "decision": decision}

    def adapt_cv(self, job_id: str, profile_label: str, model: str):
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
                job = cur.fetchone()
                if not job:
                    raise KeyError("job_not_found")
                summary = (
                    f"Profil {profile_label} ciblé pour '{job.get('title')}' chez {job.get('company')} "
                    f"({job.get('location')}). Stub IA: adapter compétences clés: {', '.join(job.get('tags', []) or [])}."
                )
                cur.execute(
                    """
                    INSERT INTO cv_variants (
                        id, user_id, job_id, application_id, profile_label, model, prompt,
                        cv_url, cover_letter_url, summary, created_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, NULL, %s, %s, %s,
                        NULL, NULL, %s, %s
                    ) RETURNING id
                    """,
                    (DEFAULT_USER_ID, job_id, profile_label, model, "stub", summary, utc_now()),
                )
                variant_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO applications (
                        id, user_id, job_id, swipe_id, status, submitted_at, channel
                    ) VALUES (
                        gen_random_uuid(), %s, %s, NULL, 'generated', NULL, NULL
                    ) RETURNING id
                    """,
                    (DEFAULT_USER_ID, job_id),
                )
                application_id = cur.fetchone()[0]
                cur.execute(
                    "UPDATE cv_variants SET application_id = %s WHERE id = %s",
                    (application_id, variant_id),
                )
            conn.commit()
        return {
            "id": variant_id,
            "job_id": job_id,
            "profile_label": profile_label,
            "model": model,
            "prompt": "stub",
            "cv_url": None,
            "cover_letter_url": None,
            "summary": summary,
            "created_at": utc_now(),
        }

    def ingest(self, jobs: List[Dict[str, Any]], replace: bool):
        for job in jobs:
            if "id" not in job:
                raise ValueError("id_required")
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor() as cur:
                # Resolve sources
                source_names = {job.get("source", "unknown") for job in jobs}
                source_map = {}
                for name in source_names:
                    cur.execute("SELECT id FROM job_sources WHERE name = %s", (name,))
                    row = cur.fetchone()
                    if row:
                        source_map[name] = row[0]
                    else:
                        cur.execute(
                            "INSERT INTO job_sources (name, kind) VALUES (%s, 'api') RETURNING id",
                            (name,)
                        )
                        source_map[name] = cur.fetchone()[0]

                # Prepare jobs
                prepared_jobs = []
                for job in jobs:
                    d = job.copy()
                    d["source_id"] = source_map.get(job.get("source", "unknown"))
                    d["source_job_id"] = job.get("source_id") # Map job.source_id -> sql.source_job_id
                    # Ensure all fields are present for SQL
                    d.setdefault("currency", None)
                    d.setdefault("salary_min", None)
                    d.setdefault("salary_max", None)
                    d.setdefault("tags", [])
                    d.setdefault("is_remote", False)
                    prepared_jobs.append(d)

                if replace:
                    cur.execute("TRUNCATE jobs RESTART IDENTITY CASCADE")
                cur.executemany(
                    """
                    INSERT INTO jobs (
                        id, source_id, source_job_id, title, company, location,
                        employment_type, seniority, salary_min, salary_max, currency,
                        is_remote, url, description, tags, published_at
                    ) VALUES (
                        %(id)s, %(source_id)s, %(source_job_id)s, %(title)s, %(company)s, %(location)s,
                        %(employment_type)s, %(seniority)s, %(salary_min)s, %(salary_max)s, %(currency)s,
                        %(is_remote)s, %(url)s, %(description)s, %(tags)s, %(published_at)s
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
                    prepared_jobs,
                )
            conn.commit()
        return {"mode": "replace" if replace else "merge", "total": len(jobs)}

    def stats(self):
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM jobs")
                total = cur.fetchone()[0]
                cur.execute(
                    "SELECT decision, count(*) FROM swipes WHERE user_id = %s GROUP BY decision",
                    (DEFAULT_USER_ID,),
                )
                counts = {row[0]: row[1] for row in cur.fetchall()}
        return {"total": total, "yes": counts.get("yes", 0), "no": counts.get("no", 0), "pending": max(total - counts.get("yes", 0) - counts.get("no", 0), 0)}

    def reset_state(self, with_cv: bool):
        with self.conn() as conn:
            ensure_user(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM swipes WHERE user_id = %s", (DEFAULT_USER_ID,))
                cur.execute("DELETE FROM applications WHERE user_id = %s", (DEFAULT_USER_ID,))
                if with_cv:
                    cur.execute("DELETE FROM cv_variants WHERE user_id = %s", (DEFAULT_USER_ID,))
            conn.commit()

    def load_sample(self):
        if not self.sample_file.exists():
            raise FileNotFoundError(f"Sample file not found: {self.sample_file}")
        with self.sample_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("Sample file must be a JSON list")
        self.ingest(data, replace=True)
        return len(data)
