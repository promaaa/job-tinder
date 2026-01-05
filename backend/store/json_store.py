import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .helpers import job_matches, normalize


class JsonStore:
    def __init__(self, root: Path | None = None):
        root_env = os.getenv("JOB_TINDER_ROOT")
        if root:
            self.root = root
        elif root_env:
            self.root = Path(root_env)
        else:
            self.root = Path(__file__).resolve().parents[2]
        self.data_dir = self.root / "data"
        self.jobs_file = self.data_dir / "jobs.json"
        self.state_file = self.data_dir / "state.json"
        self.cv_file = self.data_dir / "cv_variants.json"
        self.cv_profile_file = self.data_dir / "cv_profile.json"
        self.uploads_dir = self.data_dir / "uploads"
        self.sample_file = self.data_dir / "sample_jobs.json"

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load_json(self, path: Path, default: Any):
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return default

    def save_json(self, path: Path, payload: Any):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    # Core operations
    def list_jobs(self, *, status: str, query: str | None, company: str | None, tags: List[str], remote: str, emp_type: str | None) -> List[Dict[str, Any]]:
        jobs = self.load_json(self.jobs_file, [])
        swipes = self.load_json(self.state_file, {"swipes": {}, "applications": []}).get("swipes", {})
        results = []
        for job in jobs:
            decision = swipes.get(job.get("id"), {}).get("decision", "pending")
            if status != "all" and decision != status:
                if not (status == "pending" and decision == "pending"):
                    continue
            if not job_matches(job, query, company, tags, remote, emp_type):
                continue
            results.append({"decision": decision, **job})
        return results

    def get_job(self, job_id: str) -> Dict[str, Any]:
        jobs = {job.get("id"): job for job in self.load_json(self.jobs_file, [])}
        job = jobs.get(job_id)
        if not job:
            raise KeyError("job_not_found")
        swipes = self.load_json(self.state_file, {"swipes": {}, "applications": []}).get("swipes", {})
        decision = swipes.get(job_id, {}).get("decision", "pending")
        decided_at = swipes.get(job_id, {}).get("decided_at")
        return {"decision": decision, "decided_at": decided_at, **job}

    def swipe(self, job_id: str, decision: str):
        jobs = {job.get("id"): job for job in self.load_json(self.jobs_file, [])}
        if job_id not in jobs:
            raise KeyError("job_not_found")
        state = self.load_json(self.state_file, {"swipes": {}, "applications": []})
        swipes = state.setdefault("swipes", {})
        swipes[job_id] = {"decision": decision, "decided_at": self.utc_now()}
        self.save_json(self.state_file, state)
        return {"job_id": job_id, "decision": decision}

    def adapt_cv(self, job_id: str, profile_label: str, model: str):
        jobs = {job.get("id"): job for job in self.load_json(self.jobs_file, [])}
        job = jobs.get(job_id)
        if not job:
            raise KeyError("job_not_found")
        variants = self.load_json(self.cv_file, [])
        summary = (
            f"Profil {profile_label} ciblé pour '{job.get('title')}' chez {job.get('company')} "
            f"({job.get('location')}). Stub IA: adapter compétences clés: {', '.join(job.get('tags', []))}."
        )
        variant = {
            "id": f"cv-{len(variants)+1:04d}",
            "job_id": job_id,
            "profile_label": profile_label,
            "model": model,
            "prompt": "stub",
            "cv_url": None,
            "cover_letter_url": None,
            "summary": summary,
            "created_at": self.utc_now(),
        }
        variants.append(variant)
        self.save_json(self.cv_file, variants)

        state = self.load_json(self.state_file, {"swipes": {}, "applications": []})
        applications = state.setdefault("applications", [])
        applications.append(
            {
                "job_id": job_id,
                "profile_label": profile_label,
                "status": "generated",
                "cv_variant_id": variant["id"],
                "created_at": self.utc_now(),
            }
        )
        self.save_json(self.state_file, state)
        return variant

    def ingest(self, jobs: List[Dict[str, Any]], replace: bool):
        if replace:
            self.save_json(self.jobs_file, jobs)
            return {"mode": "replace", "total": len(jobs)}
        current = self.load_json(self.jobs_file, [])
        index: Dict[str, Dict[str, Any]] = {job.get("id"): job for job in current}
        for job in jobs:
            if "id" not in job:
                raise ValueError("id_required")
            index[job.get("id")] = job
        merged = list(index.values())
        self.save_json(self.jobs_file, merged)
        return {"mode": "merge", "total": len(merged), "added": len(jobs)}

    def stats(self):
        jobs = self.load_json(self.jobs_file, [])
        swipes = self.load_json(self.state_file, {"swipes": {}, "applications": []}).get("swipes", {})
        counts = {"yes": 0, "no": 0, "pending": 0}
        for job in jobs:
            decision = swipes.get(job.get("id"), {}).get("decision", "pending")
            counts[decision] = counts.get(decision, 0) + 1
        total = len(jobs)
        return {"total": total, **counts}

    def reset_state(self, with_cv: bool):
        self.save_json(self.state_file, {"swipes": {}, "applications": []})
        if with_cv:
            self.save_json(self.cv_file, [])

    def load_sample(self):
        jobs = self.load_json(self.sample_file, [])
        self.save_json(self.jobs_file, jobs)
        return len(jobs)

    # --- CV Profile Management ---
    
    def get_cv_profile(self) -> Dict[str, Any]:
        default = {
            "name": "",
            "email": "",
            "phone": "",
            "summary": "",
            "skills": [],
            "experience": [],
            "education": [],
            "uploaded_file": None,
        }
        return self.load_json(self.cv_profile_file, default)

    def save_cv_profile(self, profile: Dict[str, Any]):
        current = self.get_cv_profile()
        current.update(profile)
        current["updated_at"] = self.utc_now()
        self.save_json(self.cv_profile_file, current)

    def upload_cv_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        safe_name = f"cv_{self.utc_now().replace(':', '-').replace('+', '_')}_{filename}"
        file_path = self.uploads_dir / safe_name
        file_path.write_bytes(content)
        
        # Update profile with file reference
        profile = self.get_cv_profile()
        profile["uploaded_file"] = {
            "filename": filename,
            "path": str(file_path),
            "size": len(content),
            "uploaded_at": self.utc_now(),
        }
        self.save_json(self.cv_profile_file, profile)
        
        # TODO: Extract text from PDF/DOCX and populate profile fields
        return {
            "filename": filename,
            "size": len(content),
            "message": "File uploaded. Manual profile completion recommended.",
        }

    def list_cv_variants(self) -> List[Dict[str, Any]]:
        return self.load_json(self.cv_file, [])

    def get_cv_variant(self, variant_id: str) -> Dict[str, Any] | None:
        variants = self.load_json(self.cv_file, [])
        for v in variants:
            if v.get("id") == variant_id:
                return v
        return None

    def list_applications(self) -> List[Dict[str, Any]]:
        state = self.load_json(self.state_file, {"swipes": {}, "applications": []})
        applications = state.get("applications", [])
        
        # Enrich with job data
        jobs = {job.get("id"): job for job in self.load_json(self.jobs_file, [])}
        enriched = []
        for app in applications:
            job = jobs.get(app.get("job_id"), {})
            enriched.append({
                **app,
                "job_title": job.get("title", "Unknown"),
                "company": job.get("company", "Unknown"),
            })
        return enriched

