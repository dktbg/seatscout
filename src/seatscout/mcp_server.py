"""
Optional MCP server, so agents get seatscout as a first-class, typed tool
(auto-discovered, structured I/O) rather than having to shell out to the CLI.

Requires the `mcp` extra:  pip install "seatscout[mcp]"
Run:                       seatscout-mcp     (stdio transport)
"""

from __future__ import annotations


from .engine import date_range, movies_now, scan
from .providers import get_provider, list_providers


def _build_server():
    # Imported lazily so the core library has no hard dependency on `mcp`.
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("seatscout")

    @server.tool()
    def find_good_seats(
        theatre: str,
        movie: str,
        party: int = 2,
        days: int = 14,
        provider: str = "amc",
        fmt: str = "",
        top: int = 15,
    ) -> list[dict]:
        """Find showtimes that still have a block of `party` adjacent center
        seats available, ranked best-first (score 0-100, higher = more central).

        theatre:  provider theatre reference (for AMC, the site URL path,
                  e.g. "san-francisco/amc-metreon-16").
        movie:    substring of the movie slug (e.g. "odyssey").
        party:    number of adjacent seats needed.
        days:     how many days ahead to scan from today.
        provider: cinema provider id (see list_cinema_providers).
        fmt:      optional format filter (e.g. "imax", "dolby").
        top:      max results to return.
        """
        results = scan(
            provider=get_provider(provider),
            theatre=theatre,
            movie=movie,
            party=party,
            dates=date_range(days),
            fmt=fmt,
        )
        return [r.as_dict() for r in results[:top]]

    @server.tool()
    def list_movies_today(
        theatre: str, date: str = "", provider: str = "amc"
    ) -> list[dict]:
        """List movies playing at a theatre on a date (default today).

        theatre:  provider theatre reference (for AMC, the site URL path).
        date:     ISO YYYY-MM-DD; empty means today.
        provider: cinema provider id.
        """
        movies = movies_now(get_provider(provider), theatre, date or None)
        return [m.as_dict() for m in movies]

    @server.tool()
    def list_cinema_providers() -> list[str]:
        """List the cinema providers seatscout can search."""
        return list_providers()

    return server


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
