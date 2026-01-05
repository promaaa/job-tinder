import os
from functools import lru_cache

from .json_store import JsonStore
from .pg_store import PgStore


@lru_cache(maxsize=1)
def get_store():
    backend = os.getenv("STORE", "json").lower()
    if backend == "pg":
        return PgStore()
    return JsonStore()
