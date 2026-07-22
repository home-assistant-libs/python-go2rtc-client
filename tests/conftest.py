"""Asynchronous Python client for go2rtc."""

from collections.abc import AsyncGenerator
from typing import Any

from aiohttp import ClientSession
from aiointercept import aiointercept
import pytest
from syrupy import SnapshotAssertion

from go2rtc_client import Go2RtcRestClient

from . import URL, RequestTimeouts
from .syrupy import Go2RtcSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the go2rtc extension."""
    return snapshot.use_extension(Go2RtcSnapshotExtension)


@pytest.fixture
async def rest_client() -> AsyncGenerator[Go2RtcRestClient, None]:
    """Return a go2rtc rest client."""
    async with (
        ClientSession() as session,
    ):
        client_ = Go2RtcRestClient(
            session,
            URL,
        )
        yield client_


@pytest.fixture(name="responses")
async def aiointercept_fixture() -> AsyncGenerator[aiointercept, None]:
    """Return aiointercept fixture."""
    async with aiointercept(mock_external_urls=True) as mocked_responses:
        yield mocked_responses


@pytest.fixture(name="request_timeouts")
def request_timeouts_fixture(monkeypatch: pytest.MonkeyPatch) -> RequestTimeouts:
    """Capture the client side timeout passed to each request.

    aiointercept routes requests through a real test server, so the client side
    timeout is not visible in the captured request. Record it here instead.
    """
    timeouts: RequestTimeouts = {}
    original = ClientSession.request

    def _capture(
        self: ClientSession, method: str, str_or_url: Any, **kwargs: Any
    ) -> Any:
        key = (method, str(str_or_url))
        timeouts.setdefault(key, []).append(kwargs.get("timeout"))
        return original(self, method, str_or_url, **kwargs)

    monkeypatch.setattr(ClientSession, "request", _capture)
    return timeouts
