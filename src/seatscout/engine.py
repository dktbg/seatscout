"""
Provider-agnostic orchestration: scan a date range, read each showtime's
seat map (in a small thread pool), score the best block, and rank.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
from typing import Callable, List, Optional

from .models import Movie, Result, Showtime
from .providers.base import Provider
from .scoring import best_block

ProgressFn = Callable[[str, int], None]


def date_range(days: int, start: Optional[dt.date] = None) -> List[str]:
    start = start or dt.date.today()
    return [(start + dt.timedelta(days=i)).isoformat() for i in range(days)]


def movies_now(
    provider: Provider, theatre: str, date: Optional[str] = None
) -> List[Movie]:
    """Films playing at a theatre on `date` (defaults to today)."""
    return provider.list_movies(theatre, date or dt.date.today().isoformat())


def scan(
    provider: Provider,
    theatre: str,
    movie: str,
    party: int,
    dates: List[str],
    fmt: str = "",
    workers: int = 5,
    skip_sold_out: bool = True,
    on_progress: Optional[ProgressFn] = None,
) -> List[Result]:
    """Return showtimes that have a block of `party` seats, best-centered first."""
    showtimes: List[Showtime] = []
    for d in dates:
        found = provider.find_showtimes(theatre, movie, d, fmt=fmt)
        if skip_sold_out:
            found = [s for s in found if "sold out" not in s.status.lower()]
        showtimes.extend(found)
        if on_progress:
            on_progress(d, len(found))

    def evaluate(st: Showtime) -> Optional[Result]:
        block = best_block(provider.read_seat_map(st), party)
        if block is None:
            return None
        url = provider.booking_url(st, block.seats)
        return Result(showtime=st, block=block, booking_url=url)

    results: List[Result] = []
    workers = max(1, workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(evaluate, showtimes):
            if res is not None:
                results.append(res)

    results.sort(key=lambda r: r.block.score, reverse=True)
    return results
