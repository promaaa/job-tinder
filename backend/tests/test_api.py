import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.store import get_store

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


@pytest.fixture()
def sandbox(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("JOB_TINDER_ROOT", str(tmp_path))
    get_store.cache_clear()
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "jobs.json").write_text(json.dumps(SAMPLE_JOBS, indent=2), encoding="utf-8")
    (data_dir / "state.json").write_text(json.dumps({"swipes": {}, "applications": []}, indent=2), encoding="utf-8")
    (data_dir / "cv_variants.json").write_text("[]", encoding="utf-8")
    yield tmp_path
    monkeypatch.delenv("JOB_TINDER_ROOT", raising=False)
    get_store.cache_clear()


@pytest.fixture()
def client(sandbox):
    return TestClient(app)


def test_list_jobs_pending(client):
    resp = client.get("/jobs", params={"status": "pending"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2


def test_swipe_and_detail(client, sandbox: Path):
    resp = client.post("/swipes", json={"job_id": "job-001", "decision": "yes"})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "yes"

    detail = client.get("/jobs/job-001")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["decision"] == "yes"
    state = json.loads((sandbox / "data" / "state.json").read_text())
    assert state["swipes"]["job-001"]["decision"] == "yes"


def test_adapt_cv(client, sandbox: Path):
    resp = client.post(
        "/adapt-cv",
        json={"job_id": "job-001", "profile_label": "Backend Python", "model": "gpt-4.1"},
    )
    assert resp.status_code == 200
    variant = resp.json()
    assert variant["job_id"] == "job-001"

    variants = json.loads((sandbox / "data" / "cv_variants.json").read_text())
    assert len(variants) == 1
    assert variants[0]["id"] == variant["id"]

    state = json.loads((sandbox / "data" / "state.json").read_text())
    assert len(state["applications"]) == 1


def test_ingest_merge(client, sandbox: Path):
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
    resp = client.post("/ingest", json={"jobs": new_jobs, "replace": False})
    assert resp.status_code == 200
    jobs = json.loads((sandbox / "data" / "jobs.json").read_text())
    by_id = {job["id"]: job for job in jobs}
    assert len(by_id) == 3
    assert by_id["job-002"]["company"] == "InsightLab Updated"
