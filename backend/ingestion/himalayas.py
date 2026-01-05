"""
Himalayas API connector.

API: https://himalayas.app/jobs/api
Free, no authentication required.
Focus: Remote jobs with great filtering.
"""

import httpx
from typing import List, Optional, Dict, Any

from .base import JobSource, JobData


class HimalayasSource(JobSource):
    """Himalayas - Remote jobs with great company data, free API."""
    
    name = "himalayas"
    
    API_URL = "https://himalayas.app/jobs/api"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search Himalayas job listings."""
        async with httpx.AsyncClient(timeout=30) as client:
            params = {
                "limit": min(limit * 3, 100),
            }
            
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
            
            # Filter by query - more lenient matching
            if query and query.strip():
                query_lower = query.lower()
                query_words = query_lower.split()
                filtered = []
                for job in jobs:
                    categories = job.get("categories", [])
                    if isinstance(categories, list):
                        categories_str = " ".join(str(c) for c in categories)
                    else:
                        categories_str = str(categories) if categories else ""
                        
                    searchable = f"{job.get('title', '')} {job.get('companyName', '')} {job.get('description', '')} {categories_str}".lower()
                    # Match any word from query
                    if any(word in searchable for word in query_words):
                        filtered.append(job)
                jobs = filtered if filtered else jobs[:limit]  # Fall back to top jobs
            
            return [self._parse_job(job) for job in jobs[:limit]]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch job by ID."""
        return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse Himalayas job data to normalized format."""
        # Salary
        salary = None
        salary_min = data.get("minSalary")
        salary_max = data.get("maxSalary")
        
        if salary_min and salary_max:
            salary = f"${salary_min:,} - ${salary_max:,}"
        elif salary_min:
            salary = f"${salary_min:,}+"
        
        # Location/timezones
        timezones = data.get("timezones", [])
        if isinstance(timezones, list):
            location = ", ".join(str(t) for t in timezones[:3]) if timezones else "Remote Worldwide"
        else:
            location = str(timezones) if timezones else "Remote Worldwide"
        
        # Tags from categories
        tags = data.get("categories", [])
        if not isinstance(tags, list):
            tags = [str(tags)] if tags else []
        tags = [str(t) for t in tags]  # Ensure all are strings
        
        # Seniority (can be a list)
        seniority = data.get("seniority", "")
        if isinstance(seniority, list):
            seniority = " ".join(str(s) for s in seniority)
        seniority = str(seniority) if seniority else ""
        
        return JobData(
            title=data.get("title", "Sans titre"),
            company=data.get("companyName", "Entreprise"),
            location=location,
            description=data.get("description", "") or data.get("excerpt", ""),
            url=data.get("applicationLink", "") or f"https://himalayas.app/jobs/{data.get('id', '')}",
            source=self.name,
            source_id=str(data.get("id", "")),
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type="CDI",
            seniority=self.normalize_seniority(seniority),
            is_remote=True,
            tags=tags[:10],
            published_at=data.get("pubDate"),
            raw_data=data,
        )
