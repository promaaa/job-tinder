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
                "count": min(limit * 3, 50),  # Get more to filter
            }
            
            # Industry filter options: marketing, design, dev, finance, etc.
            query_lower = query.lower()
            if any(kw in query_lower for kw in ["python", "javascript", "developer", "engineer", "backend", "frontend", "fullstack", "java", "go", "rust", "node"]):
                params["industry"] = "dev"
            elif any(kw in query_lower for kw in ["design", "ui", "ux", "figma"]):
                params["industry"] = "design"
            elif any(kw in query_lower for kw in ["marketing", "seo", "growth"]):
                params["industry"] = "marketing"
            elif any(kw in query_lower for kw in ["data", "analyst", "analytics", "science"]):
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
            
            # Filter by query if specific keywords provided
            if query and query.strip():
                filtered = []
                for job in jobs:
                    industries = job.get("jobIndustry", [])
                    if isinstance(industries, str):
                        industries = [industries]
                    elif not isinstance(industries, list):
                        industries = []
                    industries_str = " ".join(str(i) for i in industries)
                    searchable = f"{job.get('jobTitle', '')} {job.get('companyName', '')} {job.get('jobDescription', '')} {industries_str}".lower()
                    # More lenient matching - check if any word from query matches
                    query_words = query_lower.split()
                    if any(word in searchable for word in query_words):
                        filtered.append(job)
                jobs = filtered if filtered else jobs  # Fall back to all if no matches
            
            return [self._parse_job(job) for job in jobs[:limit]]

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
        if isinstance(job_type, list):
            job_type = " ".join(str(t) for t in job_type)
        job_type = str(job_type).lower()
        employment_type = "CDI"
        if "contract" in job_type:
            employment_type = "freelance"
        elif "part" in job_type:
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
