from functools import lru_cache
from .db.db import DB


@lru_cache(maxsize=1)
def get_db() -> DB:
    return DB()
