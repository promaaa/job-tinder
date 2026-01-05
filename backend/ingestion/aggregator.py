"""
Job aggregator service - combines multiple sources.
"""

import asyncio
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import JobSource, JobData
from .france_travail import FranceTravailSource
from .adzuna import AdzunaSource
from .remoteok import RemoteOKSource
from .wttj import WelcomeToTheJungleSource
from .arbeitnow import ArbeitnowSource
from .jobicy import JobicySource
from .himalayas import HimalayasSource
from .findwork import FindworkSource


class JobAggregator:
    """Aggregates jobs from multiple sources."""
    
    def __init__(self):
        self.sources: Dict[str, JobSource] = {}
        self._register_sources()

    def _register_sources(self):
        """Register all available job sources."""
        # FREE - Always available (no auth required)
        self.sources["remoteok"] = RemoteOKSource()
        self.sources["arbeitnow"] = ArbeitnowSource()
        self.sources["jobicy"] = JobicySource()
        self.sources["himalayas"] = HimalayasSource()
        self.sources["findwork"] = FindworkSource()
        
        # Requires API keys
        self.sources["france_travail"] = FranceTravailSource()
        self.sources["adzuna"] = AdzunaSource()
        
        # Scraper (may break)
        self.sources["wttj"] = WelcomeToTheJungleSource()

    def get_free_sources(self) -> List[str]:
        """Return list of sources that work without API keys."""
        return ["remoteok", "arbeitnow", "jobicy", "himalayas", "findwork"]

    def list_sources(self) -> List[Dict[str, Any]]:
        """List available sources and their status."""
        result = []
        free_sources = self.get_free_sources()
        
        for name, source in self.sources.items():
            status = "available"
            note = ""
            requires_key = False
            
            if name == "france_travail":
                requires_key = True
                if not os.getenv("FRANCE_TRAVAIL_CLIENT_ID"):
                    status = "needs_config"
                    note = "Set FRANCE_TRAVAIL_CLIENT_ID and FRANCE_TRAVAIL_CLIENT_SECRET"
            
            elif name == "adzuna":
                requires_key = True
                if not os.getenv("ADZUNA_APP_ID"):
                    status = "needs_config"
                    note = "Set ADZUNA_APP_ID and ADZUNA_APP_KEY"
            
            elif name == "wttj":
                status = "scraper"
                note = "HTML scraper, may break if site changes"
            
            result.append({
                "name": name,
                "status": status,
                "note": note,
                "free": name in free_sources,
                "requires_api_key": requires_key,
            })
        
        return result

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        sources: Optional[List[str]] = None,
        limit_per_source: int = 20,
    ) -> Dict[str, Any]:
        """
        Search across multiple sources.
        
        Returns dict with jobs and metadata about each source.
        """
        # Determine which sources to use
        if sources:
            active_sources = {k: v for k, v in self.sources.items() if k in sources}
        else:
            active_sources = self.sources
        
        # Run searches in parallel
        tasks = []
        source_names = []
        
        for name, source in active_sources.items():
            tasks.append(self._search_source(source, query, location, limit_per_source))
            source_names.append(name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_jobs: List[JobData] = []
        source_stats = {}
        
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                source_stats[name] = {
                    "status": "error",
                    "error": str(result),
                    "count": 0,
                }
            else:
                all_jobs.extend(result)
                source_stats[name] = {
                    "status": "ok",
                    "count": len(result),
                }
        
        # Deduplicate by URL (different sources might have same job)
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job.url and job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
            elif not job.url:
                unique_jobs.append(job)
        
        return {
            "query": query,
            "location": location,
            "total": len(unique_jobs),
            "sources": source_stats,
            "jobs": [job.to_dict() for job in unique_jobs],
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def _search_source(
        self,
        source: JobSource,
        query: str,
        location: Optional[str],
        limit: int,
    ) -> List[JobData]:
        """Search a single source with error handling."""
        try:
            return await source.search(query, location, limit)
        except Exception as e:
            # Re-raise to be caught by gather
            raise Exception(f"{source.name}: {str(e)}")


async def search_jobs(
    query: str,
    location: Optional[str] = None,
    sources: Optional[List[str]] = None,
    limit_per_source: int = 20,
) -> Dict[str, Any]:
    """Convenience function to search jobs."""
    aggregator = JobAggregator()
    return await aggregator.search(query, location, sources, limit_per_source)
