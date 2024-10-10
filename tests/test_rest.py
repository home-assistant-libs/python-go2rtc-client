"""Asynchronous Python client for go2rtc."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp.hdrs import METH_PUT
import pytest

from go2rtc_client.models import WebRTCSdpOffer
from go2rtc_client.rest import _StreamClient, _WebRTCClient
from tests import load_fixture

from . import URL

if TYPE_CHECKING:
    from aioresponses import aioresponses
    from syrupy import SnapshotAssertion

    from go2rtc_client import Go2RtcRestClient


@pytest.mark.parametrize(
    "filename",
    [
        "streams_one.json",
        "streams_none.json",
    ],
    ids=[
        "one stream",
        "empty",
    ],
)
async def test_streams_get(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    snapshot: SnapshotAssertion,
    filename: str,
) -> None:
    """Test get streams."""
    responses.get(
        f"{URL}{_StreamClient.PATH}",
        status=200,
        body=load_fixture(filename),
    )
    resp = await rest_client.streams.list()
    assert resp == snapshot


async def test_streams_add(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
) -> None:
    """Test add stream."""
    url = f"{URL}{_StreamClient.PATH}"
    params = {
        "name": "camera.12mp_fluent",
        "src": "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
    }
    responses.put(
        url
        + "?name=camera.12mp_fluent&src=rtsp://test:test@192.168.10.105:554/Preview_06_sub",
        status=200,
    )
    await rest_client.streams.add(
        "camera.12mp_fluent", "rtsp://test:test@192.168.10.105:554/Preview_06_sub"
    )

    responses.assert_called_once_with(url, method=METH_PUT, params=params)


async def test_webrtc_offer(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    snapshot: SnapshotAssertion,
) -> None:
    """Test webrtc offer."""
    camera = "camera.12mp_fluent"
    responses.post(
        f"{URL}{_WebRTCClient.PATH}?src={camera}",
        status=200,
        body=load_fixture("webrtc_answer.json"),
    )
    resp = await rest_client.webrtc.forward_whep_sdp_offer(
        camera,
        WebRTCSdpOffer("v=0..."),
    )
    assert resp == snapshot
