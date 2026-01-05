"""
Findwork.dev API connector.

API: https://findwork.dev/api/jobs/
Free tier available, optional API key for more requests.
Focus: Developer jobs.
"""

import os
import httpx
from typing import List, Optional, Dict, Any

from .base import JobSource, JobData


class FindworkSource(JobSource):
    """Findwork.dev - Developer-focused job board."""
    
    name = "findwork"
    
    API_URL = "https://findwork.dev/api/jobs/"
    
    def __init__(self):
        # Optional API key for higher rate limits
        self.api_key = os.environ.get("FINDWORK_API_KEY")
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search Findwork job listings."""
        async with httpx.AsyncClient(timeout=30) as client:
            params = {
                "search": query,
            }
            
            if location:
                params["location"] = location
            
            headers = {
                "User-Agent": "JobTinder/1.0",
            }
            
            # Add API key if available
            if self.api_key:
                headers["Authorization"] = f"Token {self.api_key}"
            
            response = await client.get(
                self.API_URL,
                params=params,
                headers=headers,
            )
            
            if response.status_code == 401:
                # Rate limited or needs API key
                return []
            
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("results", [])
            
            return [self._parse_job(job) for job in jobs[:limit]]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch job by ID."""
        return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse Findwork job data."""
        # Remote detection
        is_remote = data.get("remote", False)
        
        # Keywords as tags
        keywords = data.get("keywords", [])
        
        # Employment type
        emp_type = data.get("employment_type", "")
        if "full" in emp_type.lower():
            employment_type = "CDI"
        elif "contract" in emp_type.lower():
            employment_type = "freelance"
        elif "part" in emp_type.lower():
            employment_type = "temps partiel"
        else:
            employment_type = "CDI"
        
        return JobData(
            title=data.get("role", "Sans titre"),
            company=data.get("company_name", "Entreprise"),
            location=data.get("location", "Remote" if is_remote else "Unknown"),
            description=data.get("text", ""),
            url=data.get("url", ""),
            source=self.name,
            source_id=str(data.get("id", "")),
            salary=None,
            employment_type=employment_type,
            is_remote=is_remote,
            tags=keywords[:10] if keywords else [],
            published_at=data.get("date_posted"),
            raw_data=data,
        )
