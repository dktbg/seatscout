"""
Live integration tests — hit amctheatres.com and assert the parsers still
extract sane data. These catch AMC changing their HTML structure before it
breaks users.

Deselected by default (they need network and are subject to AMC's live catalog).
Run explicitly:

    pytest -m integration

They assert *structural invariants* (movies exist, showtimes parse, seat maps
have seats) rather than specific titles, so they fail on real parser drift, not
on the catalog changing. If the site is simply unreachable, they skip rather
than fail, so a flaky network doesn't read as a parser break.
"""

import datetime as dt
import urllib.error

import pytest

import seatscout.providers.amc as amcmod
from seatscout.providers.amc import AMCProvider

pytestmark = pytest.mark.integration

# A reliably busy, stable theatre.
THEATRE = "san-francisco/amc-metreon-16"
KNOWN_SEAT_TYPES = {"CanReserve", "Companion", "Wheelchair", "NotASeat"}


@pytest.fixture(scope="module")
def today():
    return dt.date.today().isoformat()


@pytest.fixture(scope="module")
def live_page(today):
    """Fetch the theatre page once; skip the whole module if unreachable."""
    try:
        return amcmod._fetch(
            f"{amcmod.BASE}/movie-theatres/{THEATRE}/showtimes?date={today}"
        )
    except (urllib.error.URLError, OSError) as e:
        pytest.skip(f"amctheatres.com unreachable ({e}) — not a parser failure")


def test_list_movies_parses(live_page, monkeypatch, today):
    amc = AMCProvider()
    monkeypatch.setattr(amc, "_showtimes_page", lambda t, d: live_page)
    movies = amc.list_movies(THEATRE, today)

    assert movies, "no movies parsed — AMC likely changed the movie-link markup"
    for m in movies:
        assert m.title.strip(), f"empty title for {m.slug}"
        assert m.showtime_count >= 1, f"{m.slug} parsed with 0 showtimes"


def test_showtimes_fields_parse(live_page, monkeypatch, today):
    amc = AMCProvider()
    monkeypatch.setattr(amc, "_showtimes_page", lambda t, d: live_page)

    # Use whichever film has the most showtimes today, so this doesn't depend
    # on any particular movie being in theaters.
    movies = amc.list_movies(THEATRE, today)
    busiest = max(movies, key=lambda m: m.showtime_count)
    shows = amc.find_showtimes(THEATRE, busiest.slug, today)

    assert shows, f"no showtimes parsed for {busiest.slug}"
    for s in shows:
        assert s.sid.isdigit(), f"bad showtime id {s.sid!r}"
        assert s.time and s.time != "?", "showtime time did not parse"
        assert s.fmt and s.fmt != "?", "showtime format token did not parse"


def test_seat_map_parses(live_page, monkeypatch, today):
    amc = AMCProvider()
    monkeypatch.setattr(amc, "_showtimes_page", lambda t, d: live_page)

    movies = amc.list_movies(THEATRE, today)
    busiest = max(movies, key=lambda m: m.showtime_count)
    show = amc.find_showtimes(THEATRE, busiest.slug, today)[0]

    seats = amc.read_seat_map(show)
    # Network is confirmed up (showtimes parsed), so an empty map here means the
    # seat JSON structure changed.
    assert seats, "no seats parsed — AMC likely changed the seat JSON shape"
    assert {s.type for s in seats} & KNOWN_SEAT_TYPES, (
        "no recognized seat types — seat schema changed"
    )
    assert any(s.name for s in seats), "no named seats parsed"
