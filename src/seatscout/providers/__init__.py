"""Provider registry. Importing a provider module registers it."""

from .base import Provider, get_provider, list_providers, register
from . import amc  # noqa: F401  (import registers AMCProvider)

__all__ = ["Provider", "get_provider", "list_providers", "register"]
