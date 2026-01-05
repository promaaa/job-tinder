"""
Arbeitnow API connector.

API: https://arbeitnow.com/api/job-board-api
Free, no authentication required.
Focus: European tech jobs with remote options.
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import JobSource, JobData


class ArbeitnowSource(JobSource):
    """Arbeitnow - European tech jobs, free API."""
    
    name = "arbeitnow"
    
    API_URL = "https://arbeitnow.com/api/job-board-api"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search Arbeitnow job listings."""
        async with httpx.AsyncClient(timeout=30) as client:
            # Arbeitnow returns all jobs, filter locally
            response = await client.get(
                self.API_URL,
                headers={
                    "User-Agent": "JobTinder/1.0 (job search aggregator)",
                },
            )
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("data", [])
            
            # Filter by query
            query_lower = query.lower()
            filtered = []
            for job in jobs:
                searchable = f"{job.get('title', '')} {job.get('company_name', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
                if query_lower in searchable:
                    filtered.append(job)
            
            # Also filter by location if provided
            if location:
                loc_lower = location.lower()
                filtered = [j for j in filtered if loc_lower in j.get("location", "").lower()]
            
            return [self._parse_job(job) for job in filtered[:limit]]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch job details by slug."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.API_URL)
            response.raise_for_status()
            data = response.json()
            
            for job in data.get("data", []):
                if job.get("slug") == job_id:
                    return self._parse_job(job)
            return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse Arbeitnow job data to normalized format."""
        # Remote detection
        is_remote = data.get("remote", False)
        
        # Tags
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        
        # Job types
        job_types = data.get("job_types", [])
        employment_type = "CDI"
        if "Full Time" in job_types:
            employment_type = "CDI"
        elif "Part Time" in job_types:
            employment_type = "temps partiel"
        elif "Contract" in job_types:
            employment_type = "freelance"
        elif "Internship" in job_types:
            employment_type = "stage"
        
        return JobData(
            title=data.get("title", "Sans titre"),
            company=data.get("company_name", "Entreprise"),
            location=data.get("location", "Remote"),
            description=data.get("description", ""),
            url=data.get("url", ""),
            source=self.name,
            source_id=data.get("slug", ""),
            salary=None,  # Arbeitnow doesn't provide salary in API
            employment_type=employment_type,
            is_remote=is_remote,
            tags=tags[:10] if tags else [],
            published_at=data.get("created_at"),
            raw_data=data,
        )
