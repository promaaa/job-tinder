"""
Automatic job fetching scheduler.

Periodically fetches jobs from all free sources and imports them.
Can be run as a background task or as a cron job.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import os

from .aggregator import JobAggregator

logger = logging.getLogger(__name__)


class JobScheduler:
    """Schedules automatic job fetching from sources."""
    
    # Default search queries to fetch (can be customized)
    DEFAULT_QUERIES = [
        "python developer",
        "javascript developer", 
        "data engineer",
        "devops",
        "fullstack developer",
        "backend engineer",
        "frontend developer",
        "machine learning",
    ]
    
    # Free sources to use
    FREE_SOURCES = ["remoteok", "jobicy", "himalayas"]
    
    def __init__(
        self,
        data_dir: str = "data",
        queries: Optional[List[str]] = None,
        interval_hours: int = 6,
    ):
        self.data_dir = data_dir
        self.queries = queries or self.DEFAULT_QUERIES
        self.interval_hours = interval_hours
        self.aggregator = JobAggregator()
        self._running = False
        
        # State file to track last fetch
        self.state_file = os.path.join(data_dir, "scheduler_state.json")

    def _load_state(self) -> Dict[str, Any]:
        """Load scheduler state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_fetch": None, "total_fetched": 0, "fetch_history": []}

    def _save_state(self, state: Dict[str, Any]):
        """Save scheduler state to disk."""
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    async def fetch_all(self, store=None) -> Dict[str, Any]:
        """
        Fetch jobs from all free sources for all queries.
        
        Args:
            store: Optional store instance to save jobs to
            
        Returns:
            Summary of fetched jobs
        """
        logger.info("Starting scheduled job fetch...")
        
        all_jobs = []
        source_stats = {}
        errors = []
        
        for query in self.queries:
            try:
                logger.info(f"Fetching: {query}")
                result = await self.aggregator.search(
                    query=query,
                    sources=self.FREE_SOURCES,
                    limit_per_source=15,
                )
                
                # Collect jobs
                jobs = result.get("jobs", [])
                all_jobs.extend(jobs)
                
                # Aggregate stats
                for source, stats in result.get("sources", {}).items():
                    if source not in source_stats:
                        source_stats[source] = {"total": 0, "errors": 0}
                    source_stats[source]["total"] += stats.get("count", 0)
                    if stats.get("status") == "error":
                        source_stats[source]["errors"] += 1
                        
            except Exception as e:
                logger.error(f"Error fetching '{query}': {e}")
                errors.append({"query": query, "error": str(e)})
        
        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = job.get("url") or f"{job.get('title')}-{job.get('company')}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        # Save to store if provided
        saved_count = 0
        if store and unique_jobs:
            saved_count = await self._save_to_store(store, unique_jobs)
        
        # Update state
        state = self._load_state()
        state["last_fetch"] = datetime.utcnow().isoformat()
        state["total_fetched"] += len(unique_jobs)
        state["fetch_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(unique_jobs),
            "saved": saved_count,
            "queries": len(self.queries),
        })
        # Keep only last 100 entries
        state["fetch_history"] = state["fetch_history"][-100:]
        self._save_state(state)
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "queries_run": len(self.queries),
            "total_fetched": len(all_jobs),
            "unique_jobs": len(unique_jobs),
            "saved_to_store": saved_count,
            "sources": source_stats,
            "errors": errors,
        }
        
        logger.info(f"Fetch complete: {len(unique_jobs)} unique jobs")
        return summary

    async def _save_to_store(self, store, jobs: List[Dict]) -> int:
        """Save jobs to the store, avoiding duplicates."""
        import uuid
        
        # Use the store's ingest method which handles deduplication
        # But first, ensure all jobs have IDs and decision
        for job in jobs:
            if "id" not in job or not job["id"]:
                job["id"] = str(uuid.uuid4())[:12]
            if "decision" not in job:
                job["decision"] = "pending"
        
        if not jobs:
            return 0
        
        try:
            result = store.ingest(jobs, replace=False)
            return result.get("added", len(jobs))
        except Exception as e:
            logger.error(f"Failed to save to store: {e}")
            return 0

    async def run_once(self, store=None) -> Dict[str, Any]:
        """Run a single fetch cycle."""
        return await self.fetch_all(store)

    async def run_forever(self, store=None):
        """Run fetch cycles indefinitely at the configured interval."""
        self._running = True
        logger.info(f"Scheduler started. Fetching every {self.interval_hours} hours.")
        
        while self._running:
            try:
                await self.fetch_all(store)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Wait for next cycle
            await asyncio.sleep(self.interval_hours * 3600)

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("Scheduler stopped.")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        state = self._load_state()
        
        last_fetch = state.get("last_fetch")
        if last_fetch:
            last_fetch_dt = datetime.fromisoformat(last_fetch)
            next_fetch = last_fetch_dt + timedelta(hours=self.interval_hours)
        else:
            next_fetch = None
        
        return {
            "running": self._running,
            "interval_hours": self.interval_hours,
            "queries": self.queries,
            "sources": self.FREE_SOURCES,
            "last_fetch": last_fetch,
            "next_fetch": next_fetch.isoformat() if next_fetch else None,
            "total_fetched": state.get("total_fetched", 0),
            "recent_fetches": state.get("fetch_history", [])[-5:],
        }


# Global scheduler instance (created on demand)
_scheduler: Optional[JobScheduler] = None


def get_scheduler(
    data_dir: str = "data",
    queries: Optional[List[str]] = None,
) -> JobScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler(data_dir=data_dir, queries=queries)
    return _scheduler


async def run_fetch_once(store=None, queries: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function to run a single fetch cycle."""
    scheduler = get_scheduler(queries=queries)
    return await scheduler.run_once(store)
