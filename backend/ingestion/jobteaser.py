"""
JobTeaser scraper.
"""

import httpx
import json
from typing import List, Optional, Dict, Any
from urllib.parse import quote

from .base import JobSource, JobData


class JobTeaserSource(JobSource):
    """JobTeaser job board."""
    
    name = "jobteaser"
    
    BASE_URL = "https://www.jobteaser.com"
    API_URL = "https://www.jobteaser.com/fr/jobs.json"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> List[JobData]:
        """Search JobTeaser jobs."""
        async with httpx.AsyncClient(timeout=30) as client:
            params = {
                "query": query,
                "page": 1,
            }
            
            # Note: JobTeaser's public JSON endpoint might be restrictive
            # This is a best-effort implementation based on their common URL patterns
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }
            
            try:
                # JobTeaser often uses different paths for the JSON API
                response = await client.get(
                    self.API_URL,
                    params=params,
                    headers=headers,
                    follow_redirects=True,
                )
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                job_list = data.get("jobs", []) or data.get("results", [])
                
                jobs = []
                for job_data in job_list[:limit]:
                    try:
                        jobs.append(self._parse_job(job_data))
                    except Exception:
                        continue
                return jobs
                
            except Exception as e:
                print(f"JobTeaser error: {e}")
                return []

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse JobTeaser job data."""
        
        # Handle different potential formats
        title = data.get("title", data.get("name", "Sans titre"))
        company = data.get("company", {}).get("name", "Entreprise") if isinstance(data.get("company"), dict) else data.get("company", "Entreprise")
        
        location = data.get("location", "France")
        if isinstance(location, dict):
            location = location.get("city", "France")
            
        return JobData(
            title=title,
            company=company,
            location=location,
            description=data.get("description", ""),
            url=f"{self.BASE_URL}{data.get('url', '')}" if data.get('url', '').startswith('/') else data.get('url', ''),
            source=self.name,
            source_id=str(data.get("id", "")),
            salary=None, # Rarely in public JSON
            employment_type=self.normalize_employment_type(data.get("contract_type", "")),
            seniority=self.normalize_seniority(data.get("experience", "")),
            is_remote=False, # Hard to detect from simple JSON
            tags=data.get("tags", []),
            published_at=data.get("published_at"),
            raw_data=data,
        )

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch details for a specific job - not implemented for JobTeaser."""
        return None

