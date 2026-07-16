"""
AMC parser tests against small synthetic fixtures that mirror the real page
structure (verified against live amctheatres.com markup). No network.
"""

from seatscout.models import Showtime
from seatscout.providers.amc import AMCProvider
import seatscout.providers.amc as amcmod


def _anchor(sid, movie, theatre, fmt, time_txt, sr=""):
    """One showtime anchor as AMC emits it: aria-describedby carries the movie
    slug, theatre slug, and format token; the <time> text is the local time."""
    desc = (
        f"{movie} {movie}-{theatre} {movie}-{theatre}-{fmt} {movie}-{theatre}-{fmt}-0"
    )
    sr_html = f'<span class="sr-only">{sr}</span>' if sr else ""
    return (
        f'<a aria-describedby="{desc}" id="{sid}" href="/showtimes/{sid}">'
        f'<time dateTime="2026-07-18T02:00:00.000Z">{time_txt}</time>'
        f"{sr_html}</a>"
    )


SHOWTIMES_HTML = (
    '<h1><a href="/movies/the-odyssey-76238">The Odyssey</a></h1>'
    + _anchor(
        "100",
        "the-odyssey-76238",
        "amc-metreon-16",
        "imax70mm",
        "7:00pm",
        "Almost Full",
    )
    + _anchor(
        "101", "the-odyssey-76238", "amc-metreon-16", "dolbycinemaatamcprime", "9:00pm"
    )
    + '<h1><a href="/movies/moana-3-72474">Moana &amp; Friends</a></h1>'
    + _anchor("200", "moana-3-72474", "amc-metreon-16", "laseratamc", "6:00pm")
    # promo/nav link with no showtimes on this page
    + '<a href="/movies/coming-soon-99999">Coming Soon</a>'
)

SEATS_HTML = (
    "prefix"
    r"{\"available\":false,\"column\":1,\"row\":1,\"name\":\"\",\"type\":\"NotASeat\",\"seatTier\":\"Regular\",\"shouldDisplay\":false},"
    r"{\"available\":true,\"column\":2,\"row\":1,\"name\":\"A2\",\"type\":\"CanReserve\",\"seatTier\":\"Regular\",\"shouldDisplay\":true},"
    r"{\"available\":true,\"column\":3,\"row\":1,\"name\":\"A1\",\"type\":\"CanReserve\",\"seatTier\":\"Regular\",\"shouldDisplay\":true}"
    "suffix"
)


def test_find_showtimes_filters_and_labels(monkeypatch):
    amc = AMCProvider()
    monkeypatch.setattr(amc, "_showtimes_page", lambda t, d: SHOWTIMES_HTML)

    ody = amc.find_showtimes("amc-metreon-16", "odyssey", "2026-07-18")
    assert [s.sid for s in ody] == ["100", "101"]
    assert ody[0].fmt_label == "IMAX 70mm"
    assert ody[0].time == "7:00pm"
    assert ody[0].status == "Almost Full"

    imax = amc.find_showtimes("amc-metreon-16", "odyssey", "2026-07-18", fmt="imax")
    assert [s.sid for s in imax] == ["100"]


def test_list_movies_aggregates(monkeypatch):
    amc = AMCProvider()
    monkeypatch.setattr(amc, "_showtimes_page", lambda t, d: SHOWTIMES_HTML)

    movies = amc.list_movies("amc-metreon-16", "2026-07-18")
    by_slug = {m.slug: m for m in movies}

    # only movies with showtimes; the bare promo link is excluded
    assert set(by_slug) == {"the-odyssey-76238", "moana-3-72474"}
    ody = by_slug["the-odyssey-76238"]
    assert ody.title == "The Odyssey"
    assert ody.showtime_count == 2
    assert ody.formats == ("Dolby Cinema", "IMAX 70mm")
    # HTML entities in titles are decoded
    assert by_slug["moana-3-72474"].title == "Moana & Friends"


def test_read_seat_map_parses_escaped_json(monkeypatch):
    monkeypatch.setattr(amcmod, "_fetch", lambda url: SEATS_HTML)
    amc = AMCProvider()

    st = Showtime(
        provider="amc",
        theatre="t",
        movie="m",
        fmt="imax70mm",
        fmt_label="IMAX 70mm",
        sid="100",
        date="2026-07-18",
        time="7:00pm",
    )
    seats = amc.read_seat_map(st)
    assert len(seats) == 3
    assert {s.name for s in seats if s.reservable} == {"A1", "A2"}
    assert any(s.type == "NotASeat" for s in seats)
