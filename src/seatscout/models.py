"""Core data types, shared across providers and the scoring engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theatre:
    """A cinema location. `ref` is the provider-specific handle used in URLs."""

    ref: str
    name: str = ""
    provider: str = ""


@dataclass(frozen=True)
class Showtime:
    """A single screening. `sid` is the provider-specific showtime id."""

    provider: str
    theatre: str  # theatre ref this showtime belongs to
    movie: str  # provider movie slug/id (e.g. "the-odyssey-76238")
    fmt: str  # raw format token (e.g. "imax70mm")
    fmt_label: str  # human label (e.g. "IMAX 70mm")
    sid: str
    date: str  # theatre-local calendar date, ISO (YYYY-MM-DD)
    time: str  # theatre-local display time (e.g. "7:00pm")
    status: str = ""  # e.g. "Almost Full"; empty if not advertised


@dataclass(frozen=True)
class Movie:
    """A film playing at a theatre on a given day."""

    slug: str
    title: str
    formats: tuple  # human format labels, e.g. ("IMAX 70mm", "Dolby Cinema")
    showtime_count: int
    provider: str = ""

    def as_dict(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "formats": list(self.formats),
            "showtime_count": self.showtime_count,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class Seat:
    col: int
    row: int
    name: str  # e.g. "C17"; empty for structural gaps
    type: str  # CanReserve | Companion | Wheelchair | NotASeat | ...
    tier: str  # e.g. "Regular"
    avail: bool
    display: bool  # whether the seat is rendered in the map at all

    @property
    def reservable(self) -> bool:
        return self.avail and self.type == "CanReserve"


@dataclass(frozen=True)
class SeatBlock:
    """A contiguous run of seats and how good its centering is (0-100)."""

    seats: tuple  # seat names, left-to-right
    row: int
    score: float


@dataclass(frozen=True)
class Result:
    showtime: Showtime
    block: SeatBlock
    booking_url: str

    def as_dict(self) -> dict:
        return {
            "provider": self.showtime.provider,
            "date": self.showtime.date,
            "time": self.showtime.time,
            "format": self.showtime.fmt_label,
            "status": self.showtime.status,
            "row": self.block.row,
            "seats": list(self.block.seats),
            "score": self.block.score,
            "url": self.booking_url,
        }
