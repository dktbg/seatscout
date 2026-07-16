"""
AMC Theatres provider.

Reads amctheatres.com's public HTML. The site is a Next.js app, so each page
embeds its data as JSON in the markup; we parse that rather than scraping
rendered DOM. No login, no API key, and deliberately no interaction with the
Cloudflare-protected GraphQL endpoint.

Theatre ref = the URL path segment, e.g. "san-francisco/amc-metreon-16".
"""

from __future__ import annotations

import gzip
import re
import urllib.error
import urllib.request
from html import unescape
from typing import List, Optional
from urllib.parse import quote

from ..models import Movie, Seat, Showtime
from .base import Provider, register

BASE = "https://www.amctheatres.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)

_ANCHOR = re.compile(
    r'<a[^>]*aria-describedby="([^"]*)"[^>]*id="(\d+)"'
    r'[^>]*href="/showtimes/\2"[^>]*>(.*?)</a>',
    re.S,
)
_TIME = re.compile(r'<time[^>]*dateTime="[^"]*"[^>]*>(.*?)</time>', re.S)
_SRONLY = re.compile(r'sr-only">([^<]*)<')
_TAGS = re.compile(r"<[^>]*>")
_SEAT = re.compile(
    r'\{"available":(true|false),"column":(\d+),"row":(\d+),'
    r'"name":"([^"]*)","type":"([^"]*)","seatTier":"([^"]*)",'
    r'"shouldDisplay":(true|false)\}'
)
_MOVIE_LINK = re.compile(r'href="/movies/([a-z0-9-]+)">([^<]+)</a>')

FMT_LABEL = {
    "imax70mm": "IMAX 70mm",
    "imaxlaseratamc": "IMAX Laser",
    "dolbycinemaatamcprime": "Dolby Cinema",
    "laseratamc": "Laser at AMC",
    "opencaption": "Open Caption",
    "reclinerseating": "Recliners",
    "reald3d": "RealD 3D",
    "screenx": "ScreenX",
}


def _fetch(url: str, timeout: int = 30) -> Optional[str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


@register
class AMCProvider(Provider):
    name = "amc"

    def _showtimes_page(self, theatre: str, date: str) -> Optional[str]:
        url = f"{BASE}/movie-theatres/{theatre}/showtimes?date={date}"
        try:
            return _fetch(url)
        except (urllib.error.URLError, OSError):
            return None

    def _iter_showtimes(self, html: str, theatre: str, date: str):
        """Yield every showtime on the page as a Showtime (unfiltered)."""
        for m in _ANCHOR.finditer(html):
            desc, sid, inner = m.groups()
            toks = desc.split()
            if len(toks) < 3:
                continue
            slug = toks[0]
            token = toks[2]
            prefix = toks[1] + "-"
            fmt_tok = token[len(prefix) :] if token.startswith(prefix) else "?"
            tm = _TIME.search(inner)
            time_txt = (
                _TAGS.sub("", tm.group(1)).replace("\xa0", " ").strip() if tm else "?"
            )
            sr = _SRONLY.search(inner)
            status = sr.group(1).strip() if sr else ""
            yield Showtime(
                provider=self.name,
                theatre=theatre,
                movie=slug,
                fmt=fmt_tok,
                fmt_label=FMT_LABEL.get(fmt_tok, fmt_tok),
                sid=sid,
                date=date,
                time=time_txt,
                status=status,
            )

    def find_showtimes(
        self, theatre: str, movie: str, date: str, fmt: str = ""
    ) -> List[Showtime]:
        html = self._showtimes_page(theatre, date)
        if html is None:
            return []
        out: List[Showtime] = []
        for st in self._iter_showtimes(html, theatre, date):
            if movie.lower() not in st.movie.lower():
                continue
            if fmt and fmt.lower() not in st.fmt.lower():
                continue
            out.append(st)
        return out

    def list_movies(self, theatre: str, date: str) -> List[Movie]:
        html = self._showtimes_page(theatre, date)
        if html is None:
            return []
        titles = {}
        for slug, title in _MOVIE_LINK.findall(html):
            titles.setdefault(slug, unescape(title.strip()))
        formats: dict = {}
        counts: dict = {}
        for st in self._iter_showtimes(html, theatre, date):
            counts[st.movie] = counts.get(st.movie, 0) + 1
            formats.setdefault(st.movie, set()).add(st.fmt_label)
        # Key off showtimes, not links: promo/nav links to /movies/... would
        # otherwise appear as phantom zero-showtime movies.
        movies = [
            Movie(
                slug=slug,
                title=titles.get(slug, slug),
                formats=tuple(sorted(formats[slug])),
                showtime_count=counts[slug],
                provider=self.name,
            )
            for slug in counts
        ]
        movies.sort(key=lambda m: m.title.lower())
        return movies

    def read_seat_map(self, showtime: Showtime) -> List[Seat]:
        try:
            html = _fetch(f"{BASE}/showtimes/{showtime.sid}/seats")
        except (urllib.error.URLError, OSError):
            return []
        norm = html.replace('\\"', '"')
        seats: List[Seat] = []
        for m in _SEAT.finditer(norm):
            avail, col, row, name, typ, tier, disp = m.groups()
            seats.append(
                Seat(
                    col=int(col),
                    row=int(row),
                    name=name,
                    type=typ,
                    tier=tier,
                    avail=(avail == "true"),
                    display=(disp == "true"),
                )
            )
        return seats

    def booking_url(self, showtime: Showtime, seat_names: List[str]) -> str:
        seats = quote(",".join(seat_names), safe="")
        return f"{BASE}/showtimes/{showtime.sid}/seats?seats={seats}"
