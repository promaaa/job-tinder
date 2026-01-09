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
        """Search Jobicy job listings - prioritizing recent jobs."""
        from datetime import timedelta
        
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
            
            # Sort by publication date (most recent first)
            def get_pub_date(job):
                pub = job.get("pubDate")
                if pub:
                    try:
                        return datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    except:
                        try:
                            # Try other formats
                            return datetime.strptime(pub, "%Y-%m-%d")
                        except:
                            pass
                return datetime.min
            
            jobs.sort(key=get_pub_date, reverse=True)
            
            # Filter by freshness (default: last 48 hours)
            hours_old = kwargs.get("hours_old", 48)
            cutoff = datetime.now() - timedelta(hours=hours_old)
            fresh_jobs = []
            for job in jobs:
                pub = job.get("pubDate")
                if pub:
                    try:
                        job_date = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        if job_date.replace(tzinfo=None) >= cutoff:
                            fresh_jobs.append(job)
                            continue
                    except:
                        pass
                # Include if we need more
                if len(fresh_jobs) < limit:
                    fresh_jobs.append(job)
            
            jobs = fresh_jobs if fresh_jobs else jobs
            
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
                    # Check if ALL words from query match
                    query_words = query_lower.split()
                    if all(word in searchable for word in query_words):
                        filtered.append(job)
                jobs = filtered
            
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
