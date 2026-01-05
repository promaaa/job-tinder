from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.store import get_store


# --- Schemas ---


class SwipePayload(BaseModel):
    job_id: str
    decision: str = Field(pattern="^(yes|no)$")


class AdaptPayload(BaseModel):
    job_id: str
    profile_label: str
    model: str = "gpt-4.1"


class IngestPayload(BaseModel):
    replace: bool = False
    jobs: List[Dict[str, Any]]


# --- App ---


app = FastAPI(title="Job Tinder API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/jobs")
def list_jobs(
    status: str = "pending",
    query: Optional[str] = None,
    company: Optional[str] = None,
    tag: Optional[List[str]] = None,
    remote: str = "any",
    type: Optional[str] = None,
):
    store = get_store()
    jobs = store.list_jobs(
        status=status,
        query=query,
        company=company,
        tags=tag or [],
        remote=remote,
        emp_type=type,
    )
    return {"count": len(jobs), "items": jobs}


@app.get("/jobs/{job_id}")
def job_detail(job_id: str):
    store = get_store()
    try:
        job = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/swipes")
def swipe(payload: SwipePayload):
    store = get_store()
    try:
        store.swipe(payload.job_id, payload.decision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job_id": payload.job_id, "decision": payload.decision}


@app.post("/adapt-cv")
def adapt_cv(payload: AdaptPayload):
    store = get_store()
    try:
        variant = store.adapt_cv(payload.job_id, payload.profile_label, payload.model)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    return variant


@app.post("/ingest")
def ingest(payload: IngestPayload):
    incoming = payload.jobs
    store = get_store()
    try:
        result = store.ingest(incoming, replace=payload.replace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **result}
