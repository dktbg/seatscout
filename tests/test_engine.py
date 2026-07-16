"""Engine orchestration tests — stub provider, no network."""

from seatscout.engine import scan
from seatscout.models import Seat, Showtime
from seatscout.providers.base import Provider


def _seat(col, name, avail=True):
    return Seat(
        col=col,
        row=1,
        name=name,
        type="CanReserve",
        tier="Regular",
        avail=avail,
        display=True,
    )


def _show(sid, date, status=""):
    return Showtime(
        provider="stub",
        theatre="t",
        movie="m",
        fmt="f",
        fmt_label="F",
        sid=sid,
        date=date,
        time="7:00pm",
        status=status,
    )


class StubProvider(Provider):
    """Serves canned showtimes and seat maps keyed by sid. A sold-out
    showtime deliberately has no map, so fetching it would KeyError."""

    name = "stub"

    def __init__(self):
        self.shows = []
        self.maps = {}

    def find_showtimes(self, theatre, movie, date, fmt=""):
        return [s for s in self.shows if s.date == date]

    def list_movies(self, theatre, date):
        return []

    def read_seat_map(self, showtime):
        return self.maps[showtime.sid]

    def booking_url(self, showtime, seat_names):
        return f"stub://{showtime.sid}?seats={','.join(seat_names)}"


def _provider():
    p = StubProvider()
    p.shows = [
        _show("edge", "2026-07-18"),
        _show("center", "2026-07-18"),
        _show("soldout", "2026-07-18", status="Sold Out"),
        _show("full", "2026-07-19"),
    ]
    p.maps["center"] = [_seat(c, f"A{c}") for c in range(1, 12)]
    p.maps["edge"] = [_seat(c, f"A{c}", avail=(c <= 2)) for c in range(1, 12)]
    p.maps["full"] = [_seat(c, f"A{c}", avail=False) for c in range(1, 12)]
    return p


def test_scan_ranks_skips_sold_out_and_drops_blockless():
    results = scan(_provider(), "t", "m", party=2, dates=["2026-07-18", "2026-07-19"])
    # "full" yields no block; "soldout" is skipped before its (absent) map
    # is ever fetched — reaching it would KeyError.
    assert [r.showtime.sid for r in results] == ["center", "edge"]
    assert results[0].block.score > results[1].block.score
    assert results[0].booking_url == "stub://center?seats=A5,A6"


def test_scan_reports_progress_per_date_after_filtering():
    calls = []
    scan(
        _provider(),
        "t",
        "m",
        party=2,
        dates=["2026-07-18", "2026-07-19"],
        on_progress=lambda d, n: calls.append((d, n)),
    )
    assert calls == [("2026-07-18", 2), ("2026-07-19", 1)]
