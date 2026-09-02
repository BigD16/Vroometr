"""API config re-exports shared settings so routes can `from app.config import settings`."""

from vroometr.settings import Settings, settings

__all__ = ["Settings", "settings"]
