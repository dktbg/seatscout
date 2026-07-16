"""Command-line interface. A thin wrapper over the library core."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import List

from .engine import date_range, movies_now, scan
from .models import Result
from .providers import get_provider, list_providers


def _print_table(results: List[Result], top: int, party: int) -> None:
    shown = results[:top]
    print(
        f"\nTop {len(shown)} showtimes by best available center seats "
        f"(party of {party}):\n"
    )
    print(f"{'SCORE':>5}  {'DATE':<10} {'TIME':<8} {'FORMAT':<13} {'SEATS':<16} STATUS")
    print("-" * 82)
    for r in shown:
        st, b = r.showtime, r.block
        seats = ",".join(b.seats)
        print(
            f"{b.score:>5}  {st.date:<10} {st.time:<8} {st.fmt_label:<13} "
            f"{seats:<16} {st.status}"
        )
        print(f"       {r.booking_url}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seatscout",
        description="Find cinema showtimes that still have good center seats.",
    )
    p.add_argument(
        "--provider",
        default="amc",
        help=f"cinema provider ({', '.join(list_providers())})",
    )
    p.add_argument(
        "--theatre",
        default="san-francisco/amc-metreon-16",
        help="provider theatre reference (for AMC: the URL path, "
        "e.g. san-francisco/amc-metreon-16)",
    )
    p.add_argument(
        "--list-movies",
        action="store_true",
        help="list movies playing at the theatre on --date, then exit",
    )
    p.add_argument(
        "--date", default="", help="date for --list-movies (YYYY-MM-DD; default: today)"
    )
    p.add_argument(
        "--movie",
        default="odyssey",
        help="substring of the movie slug (default: odyssey)",
    )
    p.add_argument(
        "--format", default="", help="filter by format, e.g. imax, dolby, laser"
    )
    p.add_argument(
        "--party",
        type=int,
        default=2,
        help="number of adjacent seats needed (default: 2)",
    )
    p.add_argument(
        "--days", type=int, default=14, help="days ahead to scan (default: 14)"
    )
    p.add_argument(
        "--top", type=int, default=15, help="how many results to show (default: 15)"
    )
    p.add_argument(
        "--workers",
        type=int,
        default=5,
        help="parallel seat-map fetches; keep it polite (default: 5)",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        provider = get_provider(args.provider)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.list_movies:
        date = args.date or dt.date.today().isoformat()
        movies = movies_now(provider, args.theatre, date)
        if args.json:
            print(json.dumps([m.as_dict() for m in movies], indent=2))
            return 0
        if not movies:
            print(f"No movies found at {args.theatre} on {date}.", file=sys.stderr)
            return 1
        print(f"\nMovies playing at [{args.provider}] {args.theatre} on {date}:\n")
        print(f"{'SHOWS':>5}  {'TITLE':<44} FORMATS")
        print("-" * 82)
        for m in movies:
            print(f"{m.showtime_count:>5}  {m.title[:44]:<44} {', '.join(m.formats)}")
        return 0

    def progress(date, n):
        print(f"  scanned {date}: {n} matching showtimes", file=sys.stderr)

    print(
        f"Scanning [{args.provider}] {args.theatre} for '{args.movie}'"
        f"{' [' + args.format + ']' if args.format else ''}, "
        f"party of {args.party}, next {args.days} days...",
        file=sys.stderr,
    )

    results = scan(
        provider=provider,
        theatre=args.theatre,
        movie=args.movie,
        party=args.party,
        dates=date_range(args.days),
        fmt=args.format,
        workers=args.workers,
        on_progress=progress,
    )

    if args.json:
        print(json.dumps([r.as_dict() for r in results[: args.top]], indent=2))
        return 0

    if not results:
        print(
            "No showtimes found with a contiguous block of "
            f"{args.party} reservable seats.",
            file=sys.stderr,
        )
        return 1

    _print_table(results, args.top, args.party)
    return 0


if __name__ == "__main__":
    sys.exit(main())
