"""Entertainment — movie/series recommendations, trip planner, venue finder, etc."""

from .movie import recommend as recommend_movie
from .trip import plan_trip
from .cafe import find_venue
from .song import generate_lyrics
from .solar import optimize_solar

__all__ = [
    "recommend_movie",
    "plan_trip",
    "find_venue",
    "generate_lyrics",
    "optimize_solar",
]
