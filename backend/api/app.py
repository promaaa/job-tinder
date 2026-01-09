from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.store import get_store
from backend.outreach.generator import EmailGenerator
from backend.outreach.sender import EmailSender


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
    title: str = "Engineer"
    email: str
    phone: str = ""
    urls: Dict[str, str] = {}
    summary: str = ""
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    uploaded_file: Optional[Dict[str, Any]] = None


class ContactPayload(BaseModel):
    name: str
    email: str
    role: Optional[str] = None
    company: Optional[str] = None
    field: Optional[str] = None
    source: str = "manual"


class OutreachGeneratePayload(BaseModel):
    contact_id: str
    attach_cv: bool = True


# --- App ---


app = FastAPI(title="Job Tinder API", version="0.1.0")


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
    remote: str = "any",  # any, remote, office
    type: Optional[str] = None,  # CDI, CDD, Freelance, Stage, Alternance
    seniority: Optional[str] = None,  # junior, mid, senior
    source: Optional[str] = None,  # comma-separated sources
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    posted_within: Optional[int] = None,  # days (1, 7, 30)
    has_salary: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "date",  # date, salary, company
):
    """
    Liste les jobs avec filtres avancés.
    
    - status: pending, yes, no, all
    - query: recherche texte (titre, description)
    - company: filtrer par entreprise
    - tag: filtrer par tags (peut être répété)
    - remote: any, remote, office
    - type: CDI, CDD, Freelance, Stage, Alternance
    - seniority: junior, mid, senior
    - source: sources séparées par virgule (remoteok, linkedin, etc.)
    - location: filtrer par localisation
    - salary_min/salary_max: fourchette de salaire
    - posted_within: publiés dans les X derniers jours
    - has_salary: uniquement les offres avec salaire
    - limit/offset: pagination
    - sort_by: date, salary, company
    """
    store = get_store()
    jobs = store.list_jobs(
        status=status,
        query=query,
        company=company,
        tags=tag or [],
        remote=remote,
        emp_type=type,
    )
    
    # Additional filtering
    from datetime import datetime, timedelta
    
    filtered = []
    source_list = source.split(",") if source else None
    
    for job in jobs:
        # Source filter
        if source_list:
            job_source = (job.get("source") or "").replace("jobspy_", "")
            if job_source not in source_list and job.get("source") not in source_list:
                continue
        
        # Seniority filter
        if seniority:
            job_seniority = (job.get("seniority") or "").lower()
            if seniority.lower() not in job_seniority and job_seniority != seniority.lower():
                # Also check title for seniority hints
                title = (job.get("title") or "").lower()
                if seniority == "senior" and "senior" not in title and "sr" not in title and "lead" not in title:
                    continue
                elif seniority == "junior" and "junior" not in title and "jr" not in title and "entry" not in title:
                    continue
                elif seniority == "mid" and seniority != job_seniority:
                    if "senior" in title or "junior" in title:
                        continue
        
        # Location filter
        if location:
            job_location = (job.get("location") or "").lower()
            if location.lower() not in job_location:
                continue
        
        # Salary filters
        job_salary_min = job.get("salary_min")
        job_salary_max = job.get("salary_max")
        
        if has_salary and not job.get("salary"):
            continue
        
        if salary_min:
            if not job_salary_max or job_salary_max < salary_min:
                continue
        
        if salary_max:
            if job_salary_min and job_salary_min > salary_max:
                continue
        
        # Date filter
        if posted_within:
            pub_date = job.get("fetched_at") or job.get("published_at")
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        # Try different formats
                        if "T" in pub_date:
                            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        else:
                            dt = datetime.strptime(pub_date, "%Y-%m-%d")
                        cutoff = datetime.now().astimezone() - timedelta(days=posted_within)
                        if dt.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
                            continue
                except Exception:
                    pass
        
        filtered.append(job)
    
    # Sorting
    if sort_by == "salary":
        filtered.sort(key=lambda j: j.get("salary_max") or j.get("salary_min") or 0, reverse=True)
    elif sort_by == "company":
        filtered.sort(key=lambda j: (j.get("company") or "").lower())
    else:  # date
        # Ensure comparable values; convert to string if needed
        def date_key(job):
            val = job.get("fetched_at") or job.get("published_at")
            if isinstance(val, (int, float)):
                # treat numeric timestamps as ISO strings
                try:
                    return datetime.fromtimestamp(val).isoformat()
                except Exception:
                    return str(val)
            return val or ""
        filtered.sort(key=date_key, reverse=True)
    
    # Pagination
    total = len(filtered)
    paginated = filtered[offset:offset + limit]
    
    return {
        "count": len(paginated), 
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": paginated
    }


@app.get("/jobs/filters")
def get_filter_options():
    """
    Get available filter options based on current jobs in the database.
    Returns unique values for sources, companies, locations, tags, and salary ranges.
    """
    store = get_store()
    all_jobs = store.list_jobs(
        status="all",
        query=None,
        company=None,
        tags=[],
        remote="any",
        emp_type=None,
    )
    
    sources = set()
    companies = set()
    locations = set()
    tags = set()
    employment_types = set()
    salary_min_all = None
    salary_max_all = None
    
    for job in all_jobs:
        # Sources
        source = (job.get("source") or "").replace("jobspy_", "")
        if source:
            sources.add(source)
        
        # Companies
        company = job.get("company")
        if company and company.lower() not in ["unknown", "entreprise", ""]:
            companies.add(company)
        
        # Locations
        location = job.get("location")
        if location and location.lower() not in ["remote", "non spécifié", ""]:
            locations.add(location)
        
        # Tags
        job_tags = job.get("tags") or []
        for tag in job_tags[:5]:  # Limit per job
            if tag:
                tags.add(tag.lower())
        
        # Employment types
        emp_type = job.get("employment_type")
        if emp_type:
            employment_types.add(emp_type)
        
        # Salary range
        if job.get("salary_min"):
            if salary_min_all is None or job["salary_min"] < salary_min_all:
                salary_min_all = job["salary_min"]
        if job.get("salary_max"):
            if salary_max_all is None or job["salary_max"] > salary_max_all:
                salary_max_all = job["salary_max"]
    
    # Sort and limit
    return {
        "sources": sorted(list(sources)),
        "companies": sorted(list(companies))[:100],  # Top 100
        "locations": sorted(list(locations))[:50],
        "tags": sorted(list(tags))[:100],
        "employment_types": sorted(list(employment_types)),
        "seniority_levels": ["junior", "mid", "senior"],
        "remote_options": ["any", "remote", "office"],
        "posted_within_options": [1, 3, 7, 14, 30],
        "sort_options": ["date", "salary", "company"],
        "salary_range": {
            "min": salary_min_all or 0,
            "max": salary_max_all or 200000,
        },
        "total_jobs": len(all_jobs),
    }


@app.get("/jobs/recent")
def recent_jobs(limit: int = 20):
    """Get the most recently added jobs for harvest feedback."""
    store = get_store()
    all_jobs = store.list_jobs(
        status="all",
        query=None,
        company=None,
        tags=[],
        remote="any",
        emp_type=None,
    )
    
    # Sort by fetched_at first (most recent imports), then published_at
    def sort_key(job):
        # Prefer fetched_at for recently imported jobs
        fetched = job.get("fetched_at")
        published = job.get("published_at")
        # Use fetched_at if available, otherwise published_at
        date_str = fetched or published or ""
        # Ensure it's always a string for consistent comparison
        if not isinstance(date_str, str):
            date_str = str(date_str) if date_str else ""
        return date_str
    
    sorted_jobs = sorted(all_jobs, key=sort_key, reverse=True)
    return {"count": min(len(sorted_jobs), limit), "items": sorted_jobs[:limit]}


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
    """
    Record a swipe decision. If 'yes' (like), trigger auto-apply if configured.
    """
    store = get_store()
    try:
        job = store.get_job(payload.job_id)
        store.swipe(payload.job_id, payload.decision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = {
        "ok": True, 
        "job_id": payload.job_id, 
        "decision": payload.decision,
        "auto_apply": None,
    }
    
    # Trigger auto-apply on like
    if payload.decision == "yes":
        try:
            from backend.services.auto_apply import trigger_auto_apply
            auto_result = trigger_auto_apply(job)
            result["auto_apply"] = auto_result
        except Exception as e:
            result["auto_apply"] = {"success": False, "error": str(e)}
    
    return result


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


@app.post("/jobs/cleanup")
def cleanup_jobs(
    remove_no_description: bool = True,
    remove_sources: Optional[str] = None,  # Comma-separated list of sources to remove
):
    """
    Clean up jobs database:
    - Remove jobs without descriptions
    - Remove jobs from specific sources
    """
    store = get_store()
    all_jobs = store.list_jobs(
        status="all",
        query=None,
        company=None,
        tags=[],
        remote="any",
        emp_type=None,
    )
    
    sources_to_remove = set()
    if remove_sources:
        sources_to_remove = {s.strip().lower() for s in remove_sources.split(",")}
    
    removed_count = 0
    removed_by_source = {}
    
    for job in all_jobs:
        should_remove = False
        reason = None
        
        # Check for empty description
        if remove_no_description:
            desc = job.get("description", "") or ""
            if len(desc.strip()) < 50:  # Less than 50 chars = essentially empty
                should_remove = True
                reason = "no_description"
        
        # Check source
        source = job.get("source", "").lower()
        if source in sources_to_remove:
            should_remove = True
            reason = f"source:{source}"
        
        if should_remove:
            try:
                store.delete_job(job["id"])
                removed_count += 1
                removed_by_source[source] = removed_by_source.get(source, 0) + 1
            except Exception:
                pass
    
    return {
        "ok": True,
        "removed_count": removed_count,
        "removed_by_source": removed_by_source,
        "sources_removed": list(sources_to_remove) if sources_to_remove else None,
    }


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


# --- Scheduler / Auto-fetch ---


@app.get("/scheduler/status")
def scheduler_status():
    """Statut du scheduler d'import automatique."""
    from backend.ingestion.scheduler import get_scheduler
    scheduler = get_scheduler()
    return scheduler.get_status()


@app.post("/scheduler/fetch")
async def scheduler_fetch_now(
    queries: Optional[str] = None,
    sources: Optional[str] = None,
    profile: Optional[str] = None,
):
    """
    Lancer une récupération immédiate depuis les sources sélectionnées.
    
    - queries: requêtes de recherche séparées par virgule (optionnel)
    - sources: sources à utiliser, séparées par virgule (optionnel)
    - profile: profil de recherche prédéfini (software_engineering, data, devops_cloud, etc.)
    """
    from backend.ingestion.scheduler import JobScheduler, SEARCH_PROFILES
    
    # Use profile if specified, otherwise custom queries
    if profile and profile in SEARCH_PROFILES:
        scheduler = JobScheduler(profile=profile)
        query_list = None  # Use profile's queries
    else:
        query_list = queries.split(",") if queries else ["software engineer", "developer"]
        scheduler = JobScheduler(queries=query_list)
    
    source_list = sources.split(",") if sources else None
    store = get_store()
    
    result = await scheduler.fetch_all(store, override_sources=source_list, override_queries=query_list)
    return result


@app.get("/scheduler/profiles")
def list_scheduler_profiles():
    """Liste les profils de recherche disponibles."""
    from backend.ingestion.scheduler import SEARCH_PROFILES
    
    profiles = []
    for name, config in SEARCH_PROFILES.items():
        profiles.append({
            "name": name,
            "queries_count": len(config.get("queries", [])),
            "queries_sample": config.get("queries", [])[:3],
            "sources": config.get("sources", []),
        })
    return {"profiles": profiles}


@app.post("/scheduler/fetch/profile/{profile_name}")
async def scheduler_fetch_profile(profile_name: str):
    """
    Lancer une recherche avec un profil spécifique.
    
    Profils disponibles: software_engineering, data, devops_cloud, security, product_design, startup_tech
    """
    from backend.ingestion.scheduler import JobScheduler, SEARCH_PROFILES
    
    if profile_name not in SEARCH_PROFILES:
        raise HTTPException(status_code=400, detail=f"Profile '{profile_name}' not found. Available: {list(SEARCH_PROFILES.keys())}")
    
    scheduler = JobScheduler(profile=profile_name)
    store = get_store()
    
    result = await scheduler.fetch_all(store)
    return result


@app.post("/scheduler/fetch/full")
async def scheduler_full_fetch():
    """
    Récupération complète multi-profils.
    
    Lance une recherche sur tous les profils principaux: software, data, devops.
    """
    from backend.ingestion.scheduler import JobScheduler
    
    store = get_store()
    all_results = []
    total_saved = 0
    
    # Run multiple profiles
    for profile in ["software_engineering", "data", "devops_cloud"]:
        scheduler = JobScheduler(profile=profile)
        result = await scheduler.fetch_all(store)
        all_results.append({
            "profile": profile,
            "unique_jobs": result.get("unique_jobs", 0),
            "saved": result.get("saved_to_store", 0),
        })
        total_saved += result.get("saved_to_store", 0)
    
    return {
        "total_saved": total_saved,
        "profiles_run": all_results,
    }


# --- Contacts & Outreach ---


@app.get("/contacts")
def list_contacts():
    store = get_store()
    return store.list_contacts()


@app.post("/contacts")
def create_contact(payload: ContactPayload):
    store = get_store()
    store.add_contact(payload.model_dump())
    return {"ok": True, "message": "Contact added"}


@app.get("/contacts/{contact_id}")
def get_contact(contact_id: str):
    store = get_store()
    try:
        return store.get_contact(contact_id)
    except KeyError:
        raise HTTPException(404, "Contact not found")


@app.get("/outreach")
def list_outreach():
    store = get_store()
    return store.list_outreach()


@app.post("/outreach/generate")
def generate_outreach(payload: OutreachGeneratePayload):
    store = get_store()
    try:
        contact = store.get_contact(payload.contact_id)
        profile = store.get_cv_profile()
    except KeyError:
        raise HTTPException(404, "Contact or Profile not found")
    
    generator = EmailGenerator()
    content = generator.generate(contact, profile)
    
    attachments = []
    if payload.attach_cv:
        uploaded = profile.get("uploaded_file")
        if uploaded and "path" in uploaded:
            import os
            if os.path.exists(uploaded["path"]):
                attachments.append(uploaded["path"])
    
    msg = store.create_outreach(
        contact_id=payload.contact_id,
        subject=content["subject"],
        body=content["body"],
        generated_via="stub-ai",
        attachments=attachments
    )
    return msg


@app.post("/outreach/{msg_id}/send")
async def send_outreach(msg_id: str, background_tasks: BackgroundTasks):
    store = get_store()
    msgs = store.list_outreach()
    msg = next((m for m in msgs if m["id"] == msg_id), None)
    
    if not msg:
        raise HTTPException(404, "Message not found")
    
    if msg["status"] == "sent":
        raise HTTPException(400, "Message already sent")

    try:
        contact = store.get_contact(msg["contact_id"])
    except KeyError:
        raise HTTPException(404, "Associated contact not found")

    sender = EmailSender()

    # Define background task wrapper
    async def _send_task(message_data: Dict, email_to: str, message_id: str):
        attachments = message_data.get("attachments", [])
        success = await sender.send(message_data, email_to, attachments=attachments)
        if success:
            from datetime import datetime, timezone
            store.update_outreach(message_id, {
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat()
            })

    # Trigger sending in background to avoid blocking API
    background_tasks.add_task(_send_task, msg, contact["email"], msg_id)
    
    return {"ok": True, "message": "Sending in background", "status": "queued"}


# --- Static Files & SPA Routing ---

from fastapi.responses import FileResponse

# === PROFILE & AUTO-APPLY ===

@app.get("/profile")
def get_profile():
    """Get user profile for auto-apply."""
    from backend.services.auto_apply import UserProfile
    profile = UserProfile.load()
    # Don't expose sensitive info
    safe_profile = {k: v for k, v in profile.items() if k not in ["smtp_password"]}
    safe_profile["has_smtp_password"] = bool(profile.get("smtp_password"))
    return safe_profile


@app.put("/profile")
def update_profile(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    github_url: Optional[str] = None,
    portfolio_url: Optional[str] = None,
    location: Optional[str] = None,
    current_title: Optional[str] = None,
    years_experience: Optional[int] = None,
    skills: Optional[str] = None,
    cover_letter_template: Optional[str] = None,
    custom_intro: Optional[str] = None,
    auto_apply_enabled: Optional[bool] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
):
    """Update user profile fields."""
    from backend.services.auto_apply import UserProfile
    
    profile = UserProfile.load()
    
    # Update only provided fields
    updates = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "portfolio_url": portfolio_url,
        "location": location,
        "current_title": current_title,
        "years_experience": years_experience,
        "cover_letter_template": cover_letter_template,
        "custom_intro": custom_intro,
        "auto_apply_enabled": auto_apply_enabled,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
    }
    
    for key, value in updates.items():
        if value is not None:
            profile[key] = value
    
    # Parse skills if provided
    if skills is not None:
        profile["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
    
    # Mark SMTP as configured if all fields are present
    if all([profile.get("smtp_host"), profile.get("smtp_user"), profile.get("smtp_password")]):
        profile["smtp_configured"] = True
    
    if UserProfile.save(profile):
        return {"ok": True, "message": "Profile updated"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save profile")


@app.post("/profile/cv")
async def upload_cv(cv: UploadFile = File(...)):
    """Upload CV file (PDF, DOC, DOCX)."""
    from backend.services.auto_apply import UserProfile
    import shutil
    
    # Validate file type
    allowed_types = [".pdf", ".doc", ".docx"]
    file_ext = Path(cv.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {allowed_types}")
    
    # Save file
    cv_dir = Path(UserProfile.CV_DIR)
    cv_dir.mkdir(parents=True, exist_ok=True)
    
    # Use a clean filename
    clean_name = f"cv_{Path(cv.filename).stem}{file_ext}".replace(" ", "_")
    cv_path = cv_dir / clean_name
    
    with open(cv_path, "wb") as f:
        shutil.copyfileobj(cv.file, f)
    
    # Update profile
    profile = UserProfile.load()
    profile["cv_filename"] = clean_name
    UserProfile.save(profile)
    
    return {
        "ok": True, 
        "filename": clean_name,
        "message": "CV uploaded successfully"
    }


@app.get("/profile/auto-apply/status")
def auto_apply_status():
    """Check if auto-apply is ready and configured."""
    from backend.services.auto_apply import UserProfile
    return UserProfile.is_ready_for_auto_apply()


@app.post("/profile/auto-apply/toggle")
def toggle_auto_apply(enabled: bool):
    """Enable or disable auto-apply."""
    from backend.services.auto_apply import UserProfile
    
    profile = UserProfile.load()
    profile["auto_apply_enabled"] = enabled
    UserProfile.save(profile)
    
    return {"ok": True, "auto_apply_enabled": enabled}


@app.get("/applications")
def get_applications(limit: int = 50):
    """Get application history."""
    from backend.services.auto_apply import AutoApplyService
    service = AutoApplyService()
    return service.get_application_history(limit)


@app.post("/apply/{job_id}")
def manual_apply(job_id: str):
    """Manually trigger auto-apply for a specific job."""
    from backend.services.auto_apply import trigger_auto_apply
    
    store = get_store()
    try:
        job = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = trigger_auto_apply(job)
    return result


# === STATIC FILES ===

# Ensure FRONTEND_DIR exists
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

@app.get("/")
async def serve_root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"error": "Frontend index.html not found"}

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # If the path matches a file in dist (e.g. favicon.ico), serve it
    file_path = FRONTEND_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
        
    # Otherwise serve index.html for SPA routing
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
        
    return {"error": "Frontend build not found. Run 'npm run build' in frontend/."}



