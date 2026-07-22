"""Asynchronous Python client for go2rtc."""

from pathlib import Path

from aiohttp import ClientTimeout

type RequestTimeouts = dict[tuple[str, str], list[ClientTimeout | None]]


def assert_request_timeout(
    request_timeouts: RequestTimeouts,
    method: str,
    url: str,
    *,
    timeout: ClientTimeout | None,
) -> None:
    """Assert the client side timeout set for the given request."""
    key = (method, url)
    assert key in request_timeouts, f"no request captured for {key}"
    timeouts = request_timeouts[key]
    assert len(timeouts) == 1, f"expected one request for {key}, got {len(timeouts)}"
    assert timeouts[0] == timeout


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
