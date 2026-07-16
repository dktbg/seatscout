# Contributing guide for AI agents

Orientation and project constraints that aren't obvious from the code. For how
any specific function works, read the code — this file only covers what you'd
otherwise have to infer or wouldn't find there at all.

## What this is

A tool that finds cinema showtimes which still have good (central) seats
available, by reading each chain's public booking pages. Installable as a
library, a CLI, and an optional MCP server.

## Architecture (the shape you shouldn't have to reverse-engineer)

Three layers, bottom-up. Higher layers depend only on lower ones.

```
providers/   one adapter per cinema chain — the ONLY layer that touches the web
   base.py   Provider ABC + registry (@register)
   amc.py    AMCProvider: parses amctheatres.com

scoring.py   pure seat-centrality scoring (no I/O)
engine.py    provider-agnostic orchestration: date scanning, parallel
             seat-map fetching, ranking. Knows nothing about any chain.
models.py    frozen dataclasses passed between layers

cli.py         thin wrapper over engine  ─┐  two faces on the same core;
mcp_server.py  thin wrapper over engine  ─┘  neither contains real logic
```

Data flow for a scan: `engine.scan()` loops dates → `provider.find_showtimes()`
→ for each showtime `provider.read_seat_map()` (thread pool) → `scoring.best_block()`
→ ranked `Result`s. `list_movies` is a separate, single-page provider call.

Key point: **all chain-specific and all network code lives in `providers/`.**
Everything above it is generic. A bug in ranking is in the engine/scoring; a bug
in "wrong data from AMC" is in that provider. Keep it that way.

## Provider parsers are expected to break

Parsers are regex over undocumented HTML/embedded JSON. Site redesigns will break
them; that's normal and the fix is localized to one provider file. When a parser
breaks, fix the regex/selectors in that provider — never work around it upstream
in the engine.

## Adding a provider

Subclass `Provider`, implement `find_showtimes`, `list_movies`, `read_seat_map`,
`booking_url`, decorate with `@register`, and import it in `providers/__init__.py`
so it registers. `search_theatres` is optional. Nothing else changes — CLI, MCP,
scoring, and ranking pick it up automatically.

## Testing

Two tiers:

- **Unit tests** (default): offline, must not hit the network. Mock the
  provider's fetch/page methods; use small **synthetic** HTML fixtures that
  mirror real structure. Do **not** commit large captured pages (heavy, and
  redistributes the sites' markup).
- **Integration tests** (`@pytest.mark.integration`): hit the live sites and
  assert structural invariants, so parser drift surfaces when a chain changes
  its HTML. Deselected by default; assert invariants (data exists and parses),
  never specific titles; skip (don't fail) when the site is unreachable.

```
python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                    # offline units (fast; use in CI on every push)
.venv/bin/pytest -m integration     # live parser-drift check (schedule periodically)
```
