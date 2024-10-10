"""Asynchronous Python client for go2rtc."""

from collections.abc import AsyncGenerator, Generator

import aiohttp
from aioresponses import aioresponses
import pytest
from syrupy import SnapshotAssertion

from go2rtc_client import Go2RtcClient

from . import URL
from .syrupy import Go2RtcSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the go2rtc extension."""
    return snapshot.use_extension(Go2RtcSnapshotExtension)


@pytest.fixture
async def client() -> AsyncGenerator[Go2RtcClient, None]:
    """Return a go2rtc client."""
    async with (
        aiohttp.ClientSession() as session,
    ):
        client_ = Go2RtcClient(
            session,
            URL,
        )
        yield client_


@pytest.fixture(name="responses")
def aioresponses_fixture() -> Generator[aioresponses, None, None]:
    """Return aioresponses fixture."""
    with aioresponses() as mocked_responses:
        yield mocked_responses
