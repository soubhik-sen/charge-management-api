from __future__ import annotations


def normalize_database_url(url: str) -> str:
    """Use the installed psycopg 3 driver for provider-issued PostgreSQL URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url
