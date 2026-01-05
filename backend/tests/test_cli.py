import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_BACKEND = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_BACKEND / "cli" / "main.py"

SAMPLE_JOBS = [
    {
        "id": "job-001",
        "title": "Backend Python",
        "company": "DataForge",
        "location": "Paris",
        "employment_type": "full-time",
        "seniority": "mid",
        "is_remote": True,
        "url": "https://example.com/job-001",
        "description": "API et data pipelines",
        "tags": ["python", "fastapi"],
        "published_at": "2024-12-12T10:00:00Z",
    },
    {
        "id": "job-002",
        "title": "Data Analyst",
        "company": "InsightLab",
        "location": "Lyon",
        "employment_type": "internship",
        "seniority": "intern",
        "is_remote": False,
        "url": "https://example.com/job-002",
        "description": "SQL et dashboards",
        "tags": ["sql", "tableau"],
        "published_at": "2024-12-20T09:00:00Z",
    },
]


def write_sample(root: Path):
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sample_jobs.json").write_text(json.dumps(SAMPLE_JOBS, indent=2), encoding="utf-8")


def run_cli(root: Path, args: list[str]):
    env = os.environ.copy()
    env["JOB_TINDER_ROOT"] = str(root)
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        cwd=str(REPO_BACKEND.parent),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {result.stderr}\nstdout: {result.stdout}")
    return result


@pytest.fixture()
def sandbox(tmp_path: Path):
    write_sample(tmp_path)
    return tmp_path


def test_load_sample_and_list_pending(sandbox: Path):
    run_cli(sandbox, ["load-sample"])
    jobs_file = sandbox / "data" / "jobs.json"
    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
    assert len(jobs) == 2

    res = run_cli(sandbox, ["list", "--status", "pending"])
    assert "job-001" in res.stdout
    assert "job-002" in res.stdout


def test_swipe_and_stats(sandbox: Path):
    run_cli(sandbox, ["load-sample"])
    run_cli(sandbox, ["swipe", "job-001", "yes"])

    state = json.loads((sandbox / "data" / "state.json").read_text(encoding="utf-8"))
    assert state["swipes"]["job-001"]["decision"] == "yes"

    res = run_cli(sandbox, ["stats"])
    assert "yes: 1" in res.stdout
    assert "pending: 1" in res.stdout


def test_adapt_cv_creates_variant_and_application(sandbox: Path):
    run_cli(sandbox, ["load-sample"])
    run_cli(sandbox, ["adapt-cv", "job-001", "Backend Python", "--model", "gpt-4.1"])

    variants = json.loads((sandbox / "data" / "cv_variants.json").read_text(encoding="utf-8"))
    assert len(variants) == 1
    assert variants[0]["job_id"] == "job-001"
    assert "Backend Python" in variants[0]["profile_label"]

    state = json.loads((sandbox / "data" / "state.json").read_text(encoding="utf-8"))
    assert len(state["applications"]) == 1
    assert state["applications"][0]["cv_variant_id"] == variants[0]["id"]


def test_ingest_merges_and_dedupes(sandbox: Path):
    run_cli(sandbox, ["load-sample"])

    ingest_file = sandbox / "extra.json"
    new_jobs = [
        {**SAMPLE_JOBS[1], "company": "InsightLab Updated"},
        {
            "id": "job-003",
            "title": "PM IA",
            "company": "NovaAI",
            "location": "Remote",
            "employment_type": "contract",
            "seniority": "senior",
            "is_remote": True,
            "url": "https://example.com/job-003",
            "description": "Roadmap IA",
            "tags": ["product", "ai"],
            "published_at": "2024-12-01T08:00:00Z",
        },
    ]
    ingest_file.write_text(json.dumps(new_jobs, indent=2), encoding="utf-8")

    run_cli(sandbox, ["ingest", str(ingest_file)])

    jobs = json.loads((sandbox / "data" / "jobs.json").read_text(encoding="utf-8"))
    # should have 3 distinct ids, with job-002 updated
    by_id = {job["id"]: job for job in jobs}
    assert len(by_id) == 3
    assert by_id["job-002"]["company"] == "InsightLab Updated"
    assert "job-003" in by_id
