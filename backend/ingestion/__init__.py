"""
Job ingestion from real sources.

FREE Sources (no API key required):
- RemoteOK: Remote tech jobs worldwide
- Arbeitnow: European tech jobs
- Jobicy: Remote jobs worldwide
- Himalayas: Remote jobs with company data
- Findwork: Developer jobs (optional API key for higher limits)

Sources requiring API keys:
- France Travail (Pôle Emploi): French government job board
- Adzuna: Multi-country aggregator

Scrapers (may break):
- Welcome to the Jungle: French startup jobs
"""

from .base import JobSource, JobData
from .france_travail import FranceTravailSource
from .adzuna import AdzunaSource
from .remoteok import RemoteOKSource
from .wttj import WelcomeToTheJungleSource
from .arbeitnow import ArbeitnowSource
from .jobicy import JobicySource
from .himalayas import HimalayasSource
from .findwork import FindworkSource

# Sources available without API key
FREE_SOURCES = ["remoteok", "arbeitnow", "jobicy", "himalayas", "findwork"]

# All sources
ALL_SOURCES = FREE_SOURCES + ["france_travail", "adzuna", "wttj"]

__all__ = [
    "JobSource",
    "JobData",
    "FranceTravailSource",
    "AdzunaSource",
    "RemoteOKSource",
    "WelcomeToTheJungleSource",
    "ArbeitnowSource",
    "JobicySource",
    "HimalayasSource",
    "FindworkSource",
    "FREE_SOURCES",
    "ALL_SOURCES",
]
