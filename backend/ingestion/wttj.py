"""
Welcome to the Jungle scraper.

Note: WTTJ doesn't have a public API.
This uses their public search page with light scraping.
"""

import httpx
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import quote

from .base import JobSource, JobData


class WelcomeToTheJungleSource(JobSource):
    """Welcome to the Jungle job board."""
    
    name = "wttj"
    
    BASE_URL = "https://www.welcometothejungle.com"
    API_URL = "https://api.welcometothejungle.com/api/v1/organizations"
    
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search WTTJ jobs via their internal API."""
        async with httpx.AsyncClient(timeout=30) as client:
            # WTTJ uses Algolia for search, but we can use their public listing
            params = {
                "query": query,
                "page": 1,
                "per_page": min(limit, 30),
            }
            
            if location:
                params["aroundQuery"] = location
            
            # Try the jobs search endpoint
            search_url = f"{self.BASE_URL}/fr/jobs"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            response = await client.get(
                search_url,
                params={"query": query, "page": 1},
                headers=headers,
                follow_redirects=True,
            )
            
            if response.status_code != 200:
                return []
            
            # Extract job data from the page's embedded JSON
            jobs = self._extract_jobs_from_html(response.text)
            
            return jobs[:limit]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """WTTJ job details would require additional scraping."""
        return None

    def _extract_jobs_from_html(self, html: str) -> List[JobData]:
        """Extract job listings from WTTJ HTML page."""
        jobs = []
        
        # WTTJ embeds job data in __NEXT_DATA__ JSON
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
        if not match:
            return jobs
        
        try:
            data = json.loads(match.group(1))
            # Navigate to jobs in the data structure
            page_props = data.get("props", {}).get("pageProps", {})
            
            # Try different possible paths
            job_list = (
                page_props.get("jobs", {}).get("jobs", []) or
                page_props.get("initialJobs", []) or
                page_props.get("results", []) or
                []
            )
            
            for job_data in job_list:
                try:
                    jobs.append(self._parse_job(job_data))
                except Exception:
                    continue
                    
        except json.JSONDecodeError:
            pass
        
        return jobs

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse WTTJ job data."""
        # Handle nested organization data
        org = data.get("organization", {}) or data.get("company", {}) or {}
        
        # Location
        office = data.get("office", {}) or {}
        location = office.get("city", "") or data.get("location", "") or "France"
        
        # Contract type
        contract = data.get("contract_type", {})
        if isinstance(contract, dict):
            contract_name = contract.get("fr", "") or contract.get("en", "")
        else:
            contract_name = str(contract) if contract else ""
        
        # Remote
        remote_type = data.get("remote", "")
        is_remote = remote_type in ["fulltime", "partial", "punctual"] if remote_type else False
        
        # Salary
        salary = None
        salary_data = data.get("salary", {}) or {}
        if salary_data:
            min_sal = salary_data.get("min")
            max_sal = salary_data.get("max")
            if min_sal and max_sal:
                salary = f"{min_sal}k€ - {max_sal}k€"
        
        # Tags from profile/skills
        tags = []
        for skill in data.get("skills", [])[:10]:
            if isinstance(skill, dict):
                tags.append(skill.get("name", ""))
            else:
                tags.append(str(skill))
        
        # Build URL
        slug = data.get("slug", "")
        org_slug = org.get("slug", "")
        url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}" if slug and org_slug else ""
        
        return JobData(
            title=data.get("name", "") or data.get("title", "Sans titre"),
            company=org.get("name", "Entreprise"),
            location=location,
            description=data.get("description", "") or data.get("profile", ""),
            url=url,
            source=self.name,
            source_id=str(data.get("id", data.get("reference", ""))),
            salary=salary,
            employment_type=self.normalize_employment_type(contract_name),
            seniority=self.normalize_seniority(data.get("experience_level", "")),
            is_remote=is_remote,
            tags=[t for t in tags if t],
            published_at=data.get("published_at"),
            raw_data=data,
        )
