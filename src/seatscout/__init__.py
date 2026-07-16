"""
seatscout — find cinema showtimes that still have good center seats available.

Google can tell you *when* a movie is playing everywhere; no public data feed
tells you *which* showtimes still have good middle seats open. seatscout reads
each chain's public seat map and ranks showtimes by seat quality.
"""

from .engine import date_range, movies_now, scan
from .models import Movie, Result, Seat, SeatBlock, Showtime, Theatre
from .providers import get_provider, list_providers
from .scoring import best_block

__version__ = "0.1.0"
__all__ = [
    "scan",
    "date_range",
    "movies_now",
    "best_block",
    "get_provider",
    "list_providers",
    "Movie",
    "Result",
    "Seat",
    "SeatBlock",
    "Showtime",
    "Theatre",
]
