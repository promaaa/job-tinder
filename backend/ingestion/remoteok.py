"""
RemoteOK API connector.

API: https://remoteok.com/api
Free, no authentication required.
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import JobSource, JobData


class RemoteOKSource(JobSource):
    """RemoteOK job board - 100% remote jobs, no auth required."""
    
    name = "remoteok"
    
    API_URL = "https://remoteok.com/api"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search RemoteOK job listings - prioritizing recent jobs."""
        async with httpx.AsyncClient(timeout=30) as client:
            # RemoteOK API returns all jobs, we filter locally
            response = await client.get(
                self.API_URL,
                headers={
                    "User-Agent": "JobTinder/1.0 (job search aggregator)",
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # First item is metadata, skip it
            jobs = data[1:] if len(data) > 1 else []
            
            # Sort by date (most recent first) - RemoteOK has 'epoch' timestamp
            jobs.sort(key=lambda j: j.get("epoch", 0), reverse=True)
            
            # Filter by freshness (default: last 48 hours)
            hours_old = kwargs.get("hours_old", 48)
            now = datetime.now().timestamp()
            max_age = hours_old * 3600  # Convert to seconds
            
            fresh_jobs = []
            for job in jobs:
                job_epoch = job.get("epoch", 0)
                if job_epoch > 0 and (now - job_epoch) <= max_age:
                    fresh_jobs.append(job)
            
            # Use fresh jobs if available, otherwise fall back to all jobs
            jobs_to_filter = fresh_jobs if fresh_jobs else jobs[:100]
            
            # Filter by query
            query_lower = query.lower()
            query_terms = query_lower.split()
            filtered = []
            for job in jobs_to_filter:
                searchable = f"{job.get('position', '')} {job.get('company', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
                if all(term in searchable for term in query_terms):
                    filtered.append(job)
            
            # Apply limit
            filtered = filtered[:limit]
            
            return [self._parse_job(job) for job in filtered]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch job details by ID."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                self.API_URL,
                headers={"User-Agent": "JobTinder/1.0"},
            )
            response.raise_for_status()
            data = response.json()
            
            for job in data[1:]:
                if str(job.get("id")) == job_id:
                    return self._parse_job(job)
            
            return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse RemoteOK job data to normalized format."""
        # Extract salary
        salary = None
        salary_min = data.get("salary_min")
        salary_max = data.get("salary_max")
        
        if salary_min and salary_max:
            # RemoteOK salaries are typically in USD
            salary = f"${int(salary_min):,} - ${int(salary_max):,}".replace(",", " ")
        elif salary_min:
            salary = f"From ${int(salary_min):,}".replace(",", " ")
        
        # Tags from RemoteOK
        tags = data.get("tags", [])[:10]
        
        # Parse date
        published_at = None
        if data.get("date"):
            try:
                # Format: "2024-01-15T10:30:00"
                published_at = data["date"]
            except:
                pass
        
        # Location - all RemoteOK jobs are remote
        location = data.get("location", "Remote Worldwide")
        if not location or location == "":
            location = "Remote Worldwide"
        
        return JobData(
            title=data.get("position", "Sans titre"),
            company=data.get("company", "Unknown"),
            location=location,
            description=data.get("description", ""),
            url=data.get("url", f"https://remoteok.com/jobs/{data.get('id')}"),
            source=self.name,
            source_id=str(data.get("id", "")),
            salary=salary,
            salary_min=int(salary_min) if salary_min else None,
            salary_max=int(salary_max) if salary_max else None,
            employment_type="CDI",  # Most RemoteOK jobs are full-time
            seniority=None,
            is_remote=True,  # All RemoteOK jobs are remote
            tags=tags,
            published_at=published_at,
            raw_data=data,
        )
