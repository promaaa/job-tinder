from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.store import get_store


# --- Schemas ---


class SwipePayload(BaseModel):
    job_id: str
    decision: str = Field(pattern="^(yes|no)$")


class AdaptPayload(BaseModel):
    job_id: str
    profile_label: str = "default"
    model: str = "gpt-4.1"


class IngestPayload(BaseModel):
    replace: bool = False
    jobs: List[Dict[str, Any]]


class CVProfile(BaseModel):
    name: str
    email: str
    phone: str = ""
    summary: str = ""
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []


# --- App ---


app = FastAPI(title="Job Tinder API", version="0.1.0")


# Serve simple frontend
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    store = get_store()
    return store.stats()


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


@app.post("/jobs/reset")
def reset_jobs():
    """Reset tous les swipes et recharger les offres d'exemple"""
    store = get_store()
    store.reset_state(with_cv=False)
    count = store.load_sample()
    return {"ok": True, "message": "State reset", "jobs_loaded": count}


@app.delete("/jobs/reset")
def reset_all():
    """Reset complet: swipes, CV variants, et offres"""
    store = get_store()
    store.reset_state(with_cv=True)
    count = store.load_sample()
    return {"ok": True, "message": "Full reset", "jobs_loaded": count}


# --- CV Management ---


@app.get("/cv")
def get_cv():
    """Récupérer le profil CV actuel"""
    store = get_store()
    return store.get_cv_profile()


@app.post("/cv")
def save_cv(profile: CVProfile):
    """Sauvegarder/mettre à jour le profil CV"""
    store = get_store()
    store.save_cv_profile(profile.model_dump())
    return {"ok": True, "message": "CV saved"}


@app.post("/cv/upload")
async def upload_cv(file: UploadFile = File(...)):
    """Upload un fichier CV (PDF/DOCX) pour extraction"""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    
    ext = file.filename.lower().split(".")[-1]
    if ext not in ("pdf", "docx", "txt"):
        raise HTTPException(400, "Only PDF, DOCX, TXT supported")
    
    store = get_store()
    content = await file.read()
    result = store.upload_cv_file(file.filename, content)
    return {"ok": True, **result}


@app.get("/cv/variants")
def list_cv_variants():
    """Liste des CV adaptés générés"""
    store = get_store()
    return store.list_cv_variants()


@app.get("/cv/variants/{variant_id}")
def get_cv_variant(variant_id: str):
    """Détail d'un CV adapté"""
    store = get_store()
    variant = store.get_cv_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")
    return variant


@app.get("/applications")
def list_applications():
    """Liste des candidatures"""
    store = get_store()
    return store.list_applications()


# --- Job Sources & Search ---


@app.get("/sources")
def list_sources():
    """Liste les sources d'offres disponibles et leur statut."""
    from backend.ingestion.aggregator import JobAggregator
    aggregator = JobAggregator()
    return {"sources": aggregator.list_sources()}


@app.get("/search")
async def search_jobs(
    q: str,
    location: Optional[str] = None,
    sources: Optional[str] = None,  # comma-separated list
    limit: int = 20,
):
    """
    Recherche des offres d'emploi depuis les sources externes.
    
    - q: mots-clés (ex: "python developer")
    - location: ville ou région (ex: "Paris", "75")
    - sources: sources à utiliser, séparées par virgule (ex: "remoteok,adzuna")
    - limit: nombre max d'offres par source (défaut: 20)
    """
    from backend.ingestion.aggregator import JobAggregator
    
    source_list = sources.split(",") if sources else None
    
    aggregator = JobAggregator()
    result = await aggregator.search(
        query=q,
        location=location,
        sources=source_list,
        limit_per_source=min(limit, 50),
    )
    
    return result


@app.post("/search/import")
async def search_and_import(
    q: str,
    location: Optional[str] = None,
    sources: Optional[str] = None,
    limit: int = 20,
):
    """
    Recherche et importe les offres trouvées dans la base locale.
    
    Même paramètres que /search, mais sauvegarde les résultats.
    """
    from backend.ingestion.aggregator import JobAggregator
    
    source_list = sources.split(",") if sources else None
    
    aggregator = JobAggregator()
    result = await aggregator.search(
        query=q,
        location=location,
        sources=source_list,
        limit_per_source=min(limit, 50),
    )
    
    # Import jobs into store
    store = get_store()
    jobs = result.get("jobs", [])
    
    if jobs:
        import_result = store.ingest(jobs, replace=False)
        result["imported"] = import_result
    else:
        result["imported"] = {"total": 0, "message": "No jobs to import"}
    
    return result

