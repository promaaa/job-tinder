"""
Enhanced job fetching scheduler.

Smart scheduling with:
- Configurable search profiles (tech, data, design, etc.)
- Parallel fetching with rate limiting
- Deduplication and quality scoring
- Source health monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
import json
import os
import hashlib

from .aggregator import JobAggregator

logger = logging.getLogger(__name__)


# Pre-configured search profiles for different job categories
# NOTE: Removed 'linkedin' and 'glassdoor' - they return jobs without descriptions
SEARCH_PROFILES = {
    "software_engineering": {
        "queries": [
            "software engineer",
            "backend developer",
            "fullstack developer", 
            "frontend developer",
            "python developer",
            "javascript developer",
            "react developer",
            "node.js developer",
            "java developer",
            "golang developer",
        ],
        "sources": ["remoteok", "jobicy", "himalayas", "indeed"],
    },
    "data": {
        "queries": [
            "data engineer",
            "data scientist",
            "data analyst",
            "machine learning engineer",
            "ML engineer",
            "analytics engineer",
            "big data engineer",
        ],
        "sources": ["remoteok", "jobicy", "himalayas", "indeed"],
    },
    "devops_cloud": {
        "queries": [
            "devops engineer",
            "SRE",
            "site reliability engineer",
            "cloud engineer",
            "platform engineer",
            "kubernetes engineer",
            "AWS engineer",
            "infrastructure engineer",
        ],
        "sources": ["remoteok", "himalayas", "indeed"],
    },
    "security": {
        "queries": [
            "security engineer",
            "cybersecurity",
            "pentester",
            "security analyst",
            "application security",
            "devsecops",
        ],
        "sources": ["remoteok", "indeed", "himalayas"],
    },
    "product_design": {
        "queries": [
            "product manager",
            "product owner",
            "UX designer",
            "UI designer",
            "product designer",
        ],
        "sources": ["remoteok", "jobicy", "wttj", "himalayas"],
    },
    "startup_tech": {
        "queries": [
            "startup engineer",
            "founding engineer",
            "CTO",
            "tech lead",
            "engineering manager",
        ],
        "sources": ["remoteok", "himalayas", "wttj"],
    },
}

# Default profile for quick fetches
DEFAULT_PROFILE = "software_engineering"

# Sources that are reliable and provide full job descriptions
RELIABLE_SOURCES = ["remoteok", "jobicy", "himalayas", "indeed"]


class JobScheduler:
    """Enhanced job fetching with smart profiles and deduplication."""
    
    def __init__(
        self,
        data_dir: str = "data",
        queries: Optional[List[str]] = None,
        profile: str = DEFAULT_PROFILE,
        interval_hours: int = 6,
    ):
        self.data_dir = data_dir
        self.profile = profile
        self.interval_hours = interval_hours
        self.aggregator = JobAggregator()
        self._running = False
        
        # Custom queries override profile
        if queries:
            self.queries = queries
            self.sources = RELIABLE_SOURCES
        else:
            profile_config = SEARCH_PROFILES.get(profile, SEARCH_PROFILES[DEFAULT_PROFILE])
            self.queries = profile_config["queries"]
            self.sources = profile_config.get("sources", RELIABLE_SOURCES)
        
        # State file
        self.state_file = os.path.join(data_dir, "scheduler_state.json")
        
        # Track seen job URLs to avoid duplicates across fetches
        self.seen_urls: Set[str] = set()
        self._load_seen_urls()

    def _load_state(self) -> Dict[str, Any]:
        """Load scheduler state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_fetch": None, 
            "total_fetched": 0, 
            "fetch_history": [],
            "source_health": {},
            "seen_url_hashes": [],
        }

    def _save_state(self, state: Dict[str, Any]):
        """Save scheduler state to disk."""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_seen_urls(self):
        """Load seen URL hashes from state."""
        state = self._load_state()
        hashes = state.get("seen_url_hashes", [])
        self.seen_urls = set(hashes[-5000:])  # Keep last 5000

    def _save_seen_urls(self):
        """Save seen URL hashes to state."""
        state = self._load_state()
        state["seen_url_hashes"] = list(self.seen_urls)[-5000:]
        self._save_state(state)

    def _url_hash(self, url: str) -> str:
        """Generate short hash for URL deduplication."""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _job_signature(self, job: Dict[str, Any]) -> str:
        """Generate unique signature for a job to detect duplicates."""
        # Combine title + company + some url parts
        title = (job.get("title") or "").lower().strip()
        company = (job.get("company") or "").lower().strip()
        # Normalize common variations
        title = title.replace("senior ", "sr ").replace("junior ", "jr ")
        return hashlib.md5(f"{title}:{company}".encode()).hexdigest()[:12]

    def _score_job(self, job: Dict[str, Any]) -> float:
        """Score job quality for ranking (higher = better)."""
        score = 0.0
        
        # Has salary info (+3)
        if job.get("salary"):
            score += 3
        
        # Has good description (+2)
        desc = job.get("description", "")
        if len(desc) > 200:
            score += 2
        elif len(desc) > 50:
            score += 1
        
        # Has tags (+1)
        if job.get("tags") and len(job.get("tags", [])) >= 2:
            score += 1
        
        # Is remote (+1)
        if job.get("is_remote"):
            score += 1
        
        # Has URL (+1)
        if job.get("url"):
            score += 1
        
        # Recent posting (+2)
        if job.get("published_at"):
            try:
                pub_date = datetime.fromisoformat(job["published_at"].replace("Z", "+00:00"))
                days_old = (datetime.now().astimezone() - pub_date).days
                if days_old <= 3:
                    score += 2
                elif days_old <= 7:
                    score += 1
            except:
                pass
        
        return score

    async def fetch_all(
        self, 
        store=None, 
        override_queries: List[str] = None, 
        override_sources: List[str] = None, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch jobs from sources with enhanced deduplication and scoring.
        """
        logger.info(f"Starting enhanced job fetch (profile: {self.profile})...")
        
        queries = override_queries or self.queries
        sources = override_sources or self.sources
        
        # Filter sources to only those that are available
        available_sources = [s["name"] for s in self.aggregator.list_sources() 
                           if s["status"] in ("available", "scraper")]
        sources = [s for s in sources if s in available_sources]
        
        if not sources:
            sources = RELIABLE_SOURCES
        
        all_jobs = []
        source_stats = {}
        errors = []
        
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(3)
        
        async def fetch_query(query: str):
            async with semaphore:
                try:
                    result = await self.aggregator.search(
                        query=query,
                        sources=sources,
                        limit_per_source=limit,
                    )
                    return query, result
                except Exception as e:
                    return query, {"error": str(e), "jobs": []}
        
        # Fetch all queries in parallel (with semaphore limiting)
        tasks = [fetch_query(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                errors.append({"query": "unknown", "error": str(result)})
                continue
            
            query, data = result
            
            if "error" in data:
                errors.append({"query": query, "error": data["error"]})
                continue
            
            jobs = data.get("jobs", [])
            all_jobs.extend(jobs)
            
            # Track source stats
            for source, stats in data.get("sources", {}).items():
                if source not in source_stats:
                    source_stats[source] = {"total": 0, "errors": 0}
                source_stats[source]["total"] += stats.get("count", 0)
                if stats.get("status") == "error":
                    source_stats[source]["errors"] += 1
        
        # === DEDUPLICATION ===
        seen_signatures = set()
        unique_jobs = []
        
        for job in all_jobs:
            # Skip if we've seen this URL before
            url = job.get("url", "")
            if url:
                url_hash = self._url_hash(url)
                if url_hash in self.seen_urls:
                    continue
                self.seen_urls.add(url_hash)
            
            # Skip if same title+company
            sig = self._job_signature(job)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            
            unique_jobs.append(job)
        
        # === SCORING AND SORTING ===
        for job in unique_jobs:
            job["_quality_score"] = self._score_job(job)
        
        # Sort by quality score (highest first)
        unique_jobs.sort(key=lambda j: j.get("_quality_score", 0), reverse=True)
        
        # Remove internal score from output
        for job in unique_jobs:
            job.pop("_quality_score", None)
        
        # === SAVE TO STORE ===
        saved_count = 0
        if store and unique_jobs:
            saved_count = await self._save_to_store(store, unique_jobs)
        
        # === UPDATE STATE ===
        state = self._load_state()
        state["last_fetch"] = datetime.utcnow().isoformat()
        state["total_fetched"] += len(unique_jobs)
        
        # Update source health
        for source, stats in source_stats.items():
            health = state.get("source_health", {}).get(source, {"success": 0, "fail": 0})
            if stats["errors"] == 0:
                health["success"] = health.get("success", 0) + 1
            else:
                health["fail"] = health.get("fail", 0) + 1
            state.setdefault("source_health", {})[source] = health
        
        # Add to history
        state["fetch_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "queries_run": len(queries),
            "sources_used": sources,
            "total_fetched": len(all_jobs),
            "unique_jobs": len(unique_jobs),
            "saved": saved_count,
        })
        state["fetch_history"] = state["fetch_history"][-50:]
        
        self._save_state(state)
        self._save_seen_urls()
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "profile": self.profile,
            "queries_run": len(queries),
            "sources_used": sources,
            "total_fetched": len(all_jobs),
            "unique_jobs": len(unique_jobs),
            "saved_to_store": saved_count,
            "sources": source_stats,
            "errors": errors,
            "top_jobs": [
                {"title": j.get("title"), "company": j.get("company"), "source": j.get("source")}
                for j in unique_jobs[:5]
            ],
        }
        
        logger.info(f"Fetch complete: {len(unique_jobs)} unique jobs from {len(sources)} sources")
        return summary

    async def _save_to_store(self, store, jobs: List[Dict]) -> int:
        """Save jobs to store with proper IDs."""
        import uuid
        
        for job in jobs:
            if "id" not in job or not job["id"]:
                job["id"] = str(uuid.uuid4())
            if "decision" not in job:
                job["decision"] = "pending"
        
        if not jobs:
            return 0
        
        try:
            result = store.ingest(jobs, replace=False)
            return result.get("added", 0)
        except Exception as e:
            logger.error(f"Failed to save to store: {e}")
            return 0

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status with enhanced info."""
        state = self._load_state()
        
        last_fetch = state.get("last_fetch")
        if last_fetch:
            try:
                last_fetch_dt = datetime.fromisoformat(last_fetch)
                next_fetch = last_fetch_dt + timedelta(hours=self.interval_hours)
            except:
                next_fetch = None
        else:
            next_fetch = None
        
        return {
            "running": self._running,
            "profile": self.profile,
            "interval_hours": self.interval_hours,
            "queries": self.queries,
            "sources": self.sources,
            "available_profiles": list(SEARCH_PROFILES.keys()),
            "last_fetch": last_fetch,
            "next_fetch": next_fetch.isoformat() if next_fetch else None,
            "total_fetched": state.get("total_fetched", 0),
            "source_health": state.get("source_health", {}),
            "recent_fetches": state.get("fetch_history", [])[-5:],
        }


# Global scheduler instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler(
    data_dir: str = "data",
    queries: Optional[List[str]] = None,
    profile: str = DEFAULT_PROFILE,
) -> JobScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None or (queries and _scheduler.queries != queries):
        _scheduler = JobScheduler(data_dir=data_dir, queries=queries, profile=profile)
    return _scheduler


def list_profiles() -> Dict[str, Dict]:
    """List available search profiles."""
    return SEARCH_PROFILES


async def run_fetch_once(
    store=None, 
    queries: Optional[List[str]] = None,
    profile: str = DEFAULT_PROFILE,
) -> Dict[str, Any]:
    """Convenience function to run a single fetch cycle."""
    scheduler = get_scheduler(queries=queries, profile=profile)
    return await scheduler.fetch_all(store)
