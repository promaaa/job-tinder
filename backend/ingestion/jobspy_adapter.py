"""
Enhanced JobSpy adapter for LinkedIn, Indeed, Glassdoor, ZipRecruiter.
Uses the python-jobspy library for scraping major job boards.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

from .base import JobSource, JobData


class JobSpySource(JobSource):
    """Source using JobSpy to aggregate LinkedIn, Indeed, Glassdoor, ZipRecruiter."""
    
    # Site-specific configurations - Use 24h for fresher results
    SITE_CONFIGS = {
        "linkedin": {"hours_old": 24, "country": "france"},
        "indeed": {"hours_old": 24, "country": "france"},
        "glassdoor": {"hours_old": 24, "country": "france"},
        "zip_recruiter": {"hours_old": 24, "country": "usa"},
    }
    
    def __init__(self, sources: List[str] = None):
        self.enabled_sources = sources or ["linkedin"]
        # Use first source as primary name
        self.name = self.enabled_sources[0] if self.enabled_sources else "jobspy"

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search jobs using JobSpy with enhanced error handling."""
        
        # Import here to avoid issues if jobspy isn't installed
        try:
            from jobspy import scrape_jobs
        except ImportError:
            print("JobSpy not installed. Run: pip install python-jobspy")
            return []
        
        def do_scrape():
            try:
                # Determine country based on location or default
                country = "france"
                if location:
                    loc_lower = location.lower()
                    if any(x in loc_lower for x in ["usa", "us", "united states", "america"]):
                        country = "usa"
                    elif any(x in loc_lower for x in ["uk", "united kingdom", "london", "england"]):
                        country = "uk"
                    elif any(x in loc_lower for x in ["germany", "berlin", "munich", "deutschland"]):
                        country = "germany"
                    elif any(x in loc_lower for x in ["canada", "toronto", "vancouver"]):
                        country = "canada"
                
                # Build scrape parameters
                scrape_params = {
                    "site_name": self.enabled_sources,
                    "search_term": query,
                    "location": location or "",
                    "results_wanted": min(limit, 50),
                    "hours_old": kwargs.get("hours_old", 24),  # 24h for fresher jobs
                    "country_indeed": country,
                }
                
                # Add optional params
                if kwargs.get("is_remote"):
                    scrape_params["is_remote"] = True
                
                df = scrape_jobs(**scrape_params)
                return df
                
            except Exception as e:
                print(f"JobSpy scrape error for {self.enabled_sources}: {e}")
                return pd.DataFrame()
        
        # Run synchronous JobSpy in executor
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, do_scrape)
        
        if df is None or df.empty:
            return []
        
        jobs = []
        for _, row in df.iterrows():
            try:
                job = self._parse_row(row)
                if job and job.title and job.company:
                    jobs.append(job)
            except Exception as e:
                continue
        
        return jobs

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """JobSpy doesn't support fetching individual job details."""
        return None

    def _parse_row(self, row: Any) -> JobData:
        """Parse a JobSpy DataFrame row into JobData with enhanced extraction."""
        
        # Safe getter for pandas Series
        def safe_get(key, default=""):
            try:
                val = row.get(key)
                if pd.isna(val):
                    return default
                return val
            except:
                return default
        
        # Title and company
        title = str(safe_get('title', 'Sans titre')).strip()
        company = str(safe_get('company', 'Unknown')).strip()
        
        # Skip if missing essential info
        if not title or title == 'Sans titre' or not company or company == 'Unknown':
            if not title:
                title = "Position"
        
        # Location
        location = str(safe_get('location', '')).strip()
        is_remote = bool(safe_get('is_remote', False))
        if not location and is_remote:
            location = "Remote"
        elif not location:
            location = "Non spécifié"
        
        # Salary extraction
        salary = None
        salary_min = None
        salary_max = None
        
        min_amount = safe_get('min_amount')
        max_amount = safe_get('max_amount')
        currency = str(safe_get('currency', '€'))
        interval = str(safe_get('interval', 'yearly')).lower()
        
        if min_amount and max_amount:
            try:
                salary_min = int(float(min_amount))
                salary_max = int(float(max_amount))
                interval_label = "/an" if "year" in interval else "/mois" if "month" in interval else ""
                salary = f"{salary_min:,} - {salary_max:,} {currency}{interval_label}".replace(",", " ")
            except:
                pass
        elif min_amount:
            try:
                salary_min = int(float(min_amount))
                salary = f"{salary_min:,}+ {currency}".replace(",", " ")
            except:
                pass
        
        # Description
        description = str(safe_get('description', '')).strip()
        
        # URL
        url = str(safe_get('job_url', safe_get('job_url_direct', ''))).strip()
        
        # Source site for proper attribution
        site_name = str(safe_get('site', self.name)).lower()
        
        # Employment type
        job_type = str(safe_get('job_type', '')).lower()
        employment_type = self.normalize_employment_type(job_type)
        
        # Seniority
        job_level = str(safe_get('job_level', ''))
        seniority = self.normalize_seniority(job_level)
        
        # Extract skills/tags from description
        tags = self.extract_tags(description)
        
        # Add company industry if available
        industry = safe_get('company_industry')
        if industry and str(industry) not in tags:
            tags.insert(0, str(industry))
        
        # Published date
        date_posted = safe_get('date_posted')
        published_at = None
        if date_posted:
            try:
                if hasattr(date_posted, 'isoformat'):
                    published_at = date_posted.isoformat()
                else:
                    published_at = str(date_posted)
            except:
                pass
        
        return JobData(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            source=site_name,
            source_id=str(safe_get('id', '')),
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=employment_type,
            seniority=seniority,
            is_remote=is_remote,
            tags=tags[:10],
            published_at=published_at,
            raw_data={},  # Don't store raw to save space
        )
