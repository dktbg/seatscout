"""
Provider interface and registry.

A Provider knows how to talk to one cinema chain's public site: list its
showtimes for a movie on a date, read a showtime's seat map, and build a
deep link with seats pre-selected. Everything above this (looping dates,
parallel fetching, scoring, ranking) is provider-agnostic and lives in
`seatscout.engine`.

To add a chain, subclass Provider, implement the three abstract methods,
and decorate the class with @register.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Type

from ..models import Movie, Seat, Showtime, Theatre


class Provider(ABC):
    #: short, stable identifier used on the CLI (e.g. "amc")
    name: str = ""

    @abstractmethod
    def find_showtimes(
        self, theatre: str, movie: str, date: str, fmt: str = ""
    ) -> List[Showtime]:
        """Showtimes for `movie` (slug substring) at `theatre` on `date`
        (ISO YYYY-MM-DD). `fmt` optionally filters by format substring."""

    @abstractmethod
    def list_movies(self, theatre: str, date: str) -> List[Movie]:
        """Films playing at `theatre` on `date` (ISO YYYY-MM-DD)."""

    @abstractmethod
    def read_seat_map(self, showtime: Showtime) -> List[Seat]:
        """Every seat (available or not) for a showtime."""

    @abstractmethod
    def booking_url(self, showtime: Showtime, seat_names: List[str]) -> str:
        """Deep link to the seat-selection page with these seats pre-picked."""

    def search_theatres(self, query: str) -> List[Theatre]:
        """Optional: resolve a name/location to theatre refs. Not all
        providers implement this; the CLI accepts an explicit ref instead."""
        raise NotImplementedError(
            f"{self.name} has no theatre search yet; pass an explicit "
            f"--theatre reference."
        )


_REGISTRY: Dict[str, Type[Provider]] = {}


def register(cls: Type[Provider]) -> Type[Provider]:
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str) -> Provider:
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise KeyError(
            f"unknown provider {name!r}; available: "
            f"{', '.join(sorted(_REGISTRY)) or '(none)'}"
        )


def list_providers() -> List[str]:
    return sorted(_REGISTRY)
