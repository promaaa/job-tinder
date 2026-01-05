"""
Adzuna API connector.

API Documentation: https://developer.adzuna.com/
Requires: App ID and App Key (free tier available)
"""

import os
import httpx
from typing import List, Optional, Dict, Any

from .base import JobSource, JobData


class AdzunaSource(JobSource):
    """Adzuna job search API."""
    
    name = "adzuna"
    
    API_URL = "https://api.adzuna.com/v1/api/jobs"
    
    def __init__(self, app_id: str = None, app_key: str = None, country: str = "fr"):
        self.app_id = app_id or os.getenv("ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("ADZUNA_APP_KEY")
        self.country = country

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search Adzuna job listings."""
        if not self.app_id or not self.app_key:
            raise ValueError(
                "Adzuna credentials required. "
                "Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars. "
                "Register at https://developer.adzuna.com/"
            )

        async with httpx.AsyncClient(timeout=30) as client:
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "what": query,
                "results_per_page": min(limit, 50),
                "content-type": "application/json",
            }
            
            if location:
                params["where"] = location
            
            if kwargs.get("salary_min"):
                params["salary_min"] = kwargs["salary_min"]
            
            if kwargs.get("salary_max"):
                params["salary_max"] = kwargs["salary_max"]
            
            if kwargs.get("full_time"):
                params["full_time"] = 1
            
            if kwargs.get("permanent"):
                params["permanent"] = 1

            # Page number starts at 1
            page = kwargs.get("page", 1)
            
            response = await client.get(
                f"{self.API_URL}/{self.country}/search/{page}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            return [self._parse_job(job) for job in results]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Adzuna doesn't have a details endpoint, return None."""
        return None

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse Adzuna job data to normalized format."""
        # Extract location
        location_data = data.get("location", {})
        location_parts = []
        for area in location_data.get("area", []):
            if area:
                location_parts.append(area)
        location = ", ".join(location_parts[:2]) or "Non spécifié"
        
        # Extract salary
        salary = None
        salary_min = data.get("salary_min")
        salary_max = data.get("salary_max")
        
        if salary_min and salary_max:
            salary = f"{int(salary_min):,}€ - {int(salary_max):,}€".replace(",", " ")
        elif salary_min:
            salary = f"À partir de {int(salary_min):,}€".replace(",", " ")
        elif salary_max:
            salary = f"Jusqu'à {int(salary_max):,}€".replace(",", " ")
        
        # Determine employment type
        emp_type = None
        contract_type = data.get("contract_type")
        contract_time = data.get("contract_time")
        if contract_type:
            emp_type = self.normalize_employment_type(contract_type)
        elif contract_time:
            emp_type = self.normalize_employment_type(contract_time)
        
        # Extract tags
        description = data.get("description", "")
        title = data.get("title", "")
        category = data.get("category", {}).get("label", "")
        tags = self.extract_tags(f"{title} {description} {category}")
        
        # Add category as tag if relevant
        if category and category.lower() not in [t.lower() for t in tags]:
            tags.append(category)
        
        return JobData(
            title=data.get("title", "Sans titre"),
            company=data.get("company", {}).get("display_name", "Entreprise"),
            location=location,
            description=description,
            url=data.get("redirect_url", ""),
            source=self.name,
            source_id=data.get("id", ""),
            salary=salary,
            salary_min=int(salary_min) if salary_min else None,
            salary_max=int(salary_max) if salary_max else None,
            employment_type=emp_type,
            seniority=None,  # Not provided by Adzuna
            is_remote="remote" in title.lower() or "remote" in description.lower(),
            tags=tags[:10],
            published_at=data.get("created"),
            raw_data=data,
        )
