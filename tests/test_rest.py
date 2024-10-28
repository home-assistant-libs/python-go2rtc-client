"""Asynchronous Python client for go2rtc."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from aiohttp.hdrs import METH_PUT
from awesomeversion import AwesomeVersion
import pytest

from go2rtc_client.models import WebRTCSdpOffer
from go2rtc_client.rest import _ApplicationClient, _StreamClient, _WebRTCClient
from tests import load_fixture

from . import URL

if TYPE_CHECKING:
    from aioresponses import aioresponses
    from syrupy import SnapshotAssertion

    from go2rtc_client import Go2RtcRestClient


async def test_application_info(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    snapshot: SnapshotAssertion,
) -> None:
    """Test webrtc offer."""
    responses.get(
        f"{URL}{_ApplicationClient.PATH}",
        status=200,
        body=load_fixture("application_info_answer.json"),
    )
    resp = await rest_client.application.get_info()
    assert isinstance(resp.version, AwesomeVersion)
    assert resp == snapshot
    assert resp.to_dict() == snapshot


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
        "src": [
            "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
            "ffmpeg:camera.12mp_fluent#audio=opus",
        ],
    }
    responses.put(
        url
        + "?name=camera.12mp_fluent"
        + "&src=ffmpeg%253Acamera.12mp_fluent%2523audio%253Dopus"
        + "&src=rtsp%253A%252F%252Ftest%253Atest%2540192.168.10.105%253A554%252F"
        + "Preview_06_sub",
        status=200,
    )
    await rest_client.streams.add(
        "camera.12mp_fluent", "rtsp://test:test@192.168.10.105:554/Preview_06_sub"
    )

    responses.assert_called_once_with(url, method=METH_PUT, params=params)


@pytest.mark.parametrize(
    ("server_version", "expected_result"),
    [
        ("0.0.0", False),
        ("1.9.3", False),
        ("1.9.4", True),
        ("1.9.5", True),
        ("2.0.0", False),
        ("BLAH", False),
    ],
)
async def test_version_supported(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    server_version: str,
    expected_result: bool,
) -> None:
    """Test webrtc offer."""
    payload = json.loads(load_fixture("application_info_answer.json"))
    payload["version"] = server_version
    responses.get(
        f"{URL}{_ApplicationClient.PATH}",
        status=200,
        payload=payload,
    )
    assert await rest_client.validate_server_version() == expected_result


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
