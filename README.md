# seatscout

Find cinema showtimes that still have **good center seats** available.

Booking sites make you pick a showtime *first*, then look at the seat map — so
if you want four seats together in the middle, you end up clicking through every
date and every showtime by hand. seatscout flips it: you say the movie, how many
seats, and how far ahead to look, and it scans every showtime, reads each seat
map, and ranks showtimes by how central the still-available seats are.

## Install

```bash
pip install seatscout            # library + CLI
pip install "seatscout[mcp]"     # also installs the MCP server for agents
```

Requires Python 3.11+. The core has no third-party dependencies.

## CLI

```bash
# 4 seats, next 3 weeks, IMAX only, at one AMC theatre
seatscout --provider amc \
          --theatre san-francisco/amc-metreon-16 \
          --movie odyssey --party 4 --days 21 --format imax
```

```
Top 3 showtimes by best available center seats (party of 4):

SCORE  DATE       TIME     FORMAT        SEATS            STATUS
----------------------------------------------------------------------------------
 70.8  2026-08-04 10:00pm  IMAX 70mm     C16,C17,C18,C19
       https://www.amctheatres.com/showtimes/143822412/seats?seats=C19%2CC18%2CC17%2CC16
 65.4  2026-07-27 2:00pm   IMAX 70mm     B16,B17,B18,B19  Almost Full
       https://www.amctheatres.com/showtimes/143822447/seats?seats=B19%2CB18%2CB17%2CB16
```

Each row includes a deep link with the seats **pre-selected** — one click to checkout.

Add `--json` for machine-readable output (handy for scripts and shell-driven agents).

## Use as a library

```python
from seatscout import scan, date_range, get_provider

results = scan(
    provider=get_provider("amc"),
    theatre="san-francisco/amc-metreon-16",
    movie="odyssey", party=4, dates=date_range(21), fmt="imax",
)
for r in results[:5]:
    print(r.showtime.date, r.showtime.time, r.block.seats, r.block.score, r.booking_url)
```

## Use from an agent (MCP)

With the `[mcp]` extra installed, expose seatscout as a typed, auto-discovered tool:

```json
{
  "mcpServers": {
    "seatscout": { "command": "seatscout-mcp" }
  }
}
```

Tools: `find_good_seats(theatre, movie, party, days, provider, fmt, top)` and
`list_cinema_providers()`. Agents that have shell access can equally just call
the CLI with `--json`; MCP adds automatic discovery and structured I/O.

## How seat scoring works

Each candidate is a **contiguous run of `party` reservable seats in one row**,
scored 0–100 (higher = better center). Two penalties pull it down:

- **Horizontal (60%)** — how far the block's center is from the row's midpoint.
- **Vertical (40%)** — how far the row is from ~62% back, the preferred depth.

Wheelchair/companion seats are excluded, sold-out showtimes are skipped, and a
run breaks across any aisle or taken seat, so a "block" is always seats you can
actually sit in together. Tune the weights in `seatscout/scoring.py`.

## Adding a cinema provider

Chains don't share a seat API, so each is its own adapter behind a common
interface. To add one, subclass `Provider`, implement three methods, and
register it:

```python
from seatscout.providers.base import Provider, register
from seatscout.models import Seat, Showtime

@register
class RegalProvider(Provider):
    name = "regal"
    def find_showtimes(self, theatre, movie, date, fmt=""): ...
    def read_seat_map(self, showtime): ...
    def booking_url(self, showtime, seat_names): ...
```

Everything else — date scanning, parallel fetching, scoring, ranking, CLI, and
MCP — works unchanged.

## Responsible use

- Reads only pages the sites serve publicly; **does not** bypass bot protections,
  log in, or automate purchases.
- Defaults to a small parallel fetch pool — keep it modest so you don't hammer
  anyone's servers.
- Scraping may conflict with a site's Terms of Service. This is a personal
  convenience tool provided as-is; you are responsible for how you use it.
- Site markup changes will break parsers from time to time — that's the nature
  of scraping undocumented pages. Fixes are usually localized to one provider.

MIT licensed.
