"""
Jobicy API connector.

API: https://jobicy.com/api/v2/remote-jobs
Free, no authentication required.
Focus: Remote jobs worldwide.
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import JobSource, JobData


class JobicySource(JobSource):
    """Jobicy - Remote jobs worldwide, free API."""
    
    name = "jobicy"
    
    API_URL = "https://jobicy.com/api/v2/remote-jobs"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search Jobicy job listings."""
        async with httpx.AsyncClient(timeout=30) as client:
            params = {
                "count": min(limit * 2, 50),  # Get more to filter
                "tag": query,  # Jobicy uses tags for filtering
            }
            
            # Industry filter options: marketing, design, dev, finance, etc.
            if any(kw in query.lower() for kw in ["python", "javascript", "developer", "engineer", "backend", "frontend", "fullstack"]):
                params["industry"] = "dev"
            elif any(kw in query.lower() for kw in ["design", "ui", "ux", "figma"]):
                params["industry"] = "design"
            elif any(kw in query.lower() for kw in ["marketing", "seo", "growth"]):
                params["industry"] = "marketing"
            elif any(kw in query.lower() for kw in ["data", "analyst", "analytics"]):
                params["industry"] = "data"
            
            response = await client.get(
                self.API_URL,
                params=params,
                headers={
                    "User-Agent": "JobTinder/1.0 (job search aggregator)",
                },
            )
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("jobs", [])
            
            # Additional filtering by query
            query_lower = query.lower()
            filtered = []
            for job in jobs:
                searchable = f"{job.get('jobTitle', '')} {job.get('companyName', '')} {job.get('jobDescription', '')} {' '.join(job.get('jobIndustry', []))}".lower()
                if query_lower in searchable or not query:
                    filtered.append(job)
            
            return [self._parse_job(job) for job in filtered[:limit]]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Jobicy doesn't have a single job endpoint."""
        return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse Jobicy job data to normalized format."""
        # Salary parsing
        salary = None
        salary_min = None
        salary_max = None
        
        ann_salary_min = data.get("annualSalaryMin")
        ann_salary_max = data.get("annualSalaryMax")
        
        if ann_salary_min and ann_salary_max:
            salary = f"${int(ann_salary_min):,} - ${int(ann_salary_max):,}/year"
            salary_min = int(ann_salary_min)
            salary_max = int(ann_salary_max)
        elif ann_salary_min:
            salary = f"${int(ann_salary_min):,}+/year"
            salary_min = int(ann_salary_min)
        
        # Job type
        job_type = data.get("jobType", "")
        employment_type = "CDI"
        if "contract" in job_type.lower():
            employment_type = "freelance"
        elif "part" in job_type.lower():
            employment_type = "temps partiel"
        
        # Location
        location = data.get("jobGeo", "Remote")
        if isinstance(location, list):
            location = ", ".join(location) if location else "Remote"
        
        # Tags from industry
        tags = data.get("jobIndustry", [])
        if isinstance(tags, str):
            tags = [tags]
        
        return JobData(
            title=data.get("jobTitle", "Sans titre"),
            company=data.get("companyName", "Entreprise"),
            location=location,
            description=data.get("jobDescription", ""),
            url=data.get("url", ""),
            source=self.name,
            source_id=str(data.get("id", "")),
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=employment_type,
            is_remote=True,  # Jobicy is all remote jobs
            tags=tags[:10] if tags else [],
            published_at=data.get("pubDate"),
            raw_data=data,
        )
