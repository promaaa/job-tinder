"""Base classes for job sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib


@dataclass
class JobData:
    """Normalized job data structure."""
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str  # e.g., "france_travail", "adzuna", "remoteok"
    source_id: str  # ID from the original source
    
    # Optional fields
    salary: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    employment_type: Optional[str] = None  # CDI, CDD, freelance, internship
    seniority: Optional[str] = None  # junior, mid, senior
    is_remote: bool = False
    tags: List[str] = field(default_factory=list)
    published_at: Optional[str] = None
    expires_at: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Generate unique ID from source and source_id."""
        key = f"{self.source}:{self.source_id}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage."""
        d = asdict(self)
        d["id"] = self.id
        # Remove raw_data from output (too heavy)
        d.pop("raw_data", None)
        return d


class JobSource(ABC):
    """Abstract base class for job sources."""
    
    name: str = "unknown"
    
    @abstractmethod
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search for jobs matching criteria."""
        pass

    @abstractmethod
    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch full details for a specific job."""
        pass

    def normalize_employment_type(self, raw: str) -> Optional[str]:
        """Normalize employment type to standard values."""
        raw_lower = raw.lower() if raw else ""
        mappings = {
            "cdi": "CDI",
            "permanent": "CDI",
            "full-time": "CDI",
            "full_time": "CDI",
            "cdd": "CDD",
            "contract": "CDD",
            "temporary": "CDD",
            "fixed-term": "CDD",
            "freelance": "Freelance",
            "contractor": "Freelance",
            "self-employed": "Freelance",
            "internship": "Stage",
            "stage": "Stage",
            "intern": "Stage",
            "apprenticeship": "Alternance",
            "alternance": "Alternance",
            "part-time": "Temps partiel",
            "part_time": "Temps partiel",
        }
        for key, value in mappings.items():
            if key in raw_lower:
                return value
        return raw if raw else None

    def normalize_seniority(self, raw: str) -> Optional[str]:
        """Normalize seniority level."""
        raw_lower = raw.lower() if raw else ""
        if any(x in raw_lower for x in ["junior", "entry", "débutant", "0-2"]):
            return "junior"
        if any(x in raw_lower for x in ["senior", "lead", "principal", "5+", "expert"]):
            return "senior"
        if any(x in raw_lower for x in ["mid", "intermediate", "2-5", "confirmé"]):
            return "mid"
        if any(x in raw_lower for x in ["intern", "stage", "student"]):
            return "intern"
        return None

    def extract_tags(self, text: str, skills_list: List[str] = None) -> List[str]:
        """Extract skill tags from text."""
        default_skills = [
            "python", "javascript", "typescript", "java", "c++", "go", "rust",
            "react", "vue", "angular", "node.js", "django", "fastapi", "flask",
            "sql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
            "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
            "git", "ci/cd", "agile", "scrum",
            "machine learning", "deep learning", "nlp", "computer vision",
            "data science", "analytics", "tableau", "power bi",
            "figma", "sketch", "ux", "ui",
        ]
        skills = skills_list or default_skills
        text_lower = text.lower()
        found = []
        for skill in skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found[:10]  # Limit to 10 tags
