"""Asynchronous Python client for go2rtc."""

from pathlib import Path


def load_fixture(filename: str) -> Path:
    """Load a fixture."""
    return Path(__package__) / "fixtures" / filename


def load_fixture_bytes(filename: str) -> bytes:
    """Load a fixture and return bytes."""
    return load_fixture(filename).read_bytes()


def load_fixture_str(filename: str) -> str:
    """Load a fixture and return str."""
    return load_fixture(filename).read_text(encoding="utf-8")


URL = "http://localhost:1984"
