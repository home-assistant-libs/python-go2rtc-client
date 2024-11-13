"""Asynchronous Python client for go2rtc."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext as does_not_raise
import json
from typing import TYPE_CHECKING, Any

from aiohttp import ClientTimeout
from aiohttp.hdrs import METH_PUT
from awesomeversion import AwesomeVersion
import pytest

from go2rtc_client.exceptions import Go2RtcVersionError
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
    ["streams_one.json", "streams_none.json", "streams_without_producers.json"],
    ids=[
        "one stream",
        "empty",
        "without producers",
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


async def test_streams_add_list(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
) -> None:
    """Test add stream."""
    url = f"{URL}{_StreamClient.PATH}"
    camera = "camera.12mp_fluent"
    params = {
        "name": camera,
        "src": [
            "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
            f"ffmpeg:{camera}#audio=opus",
        ],
    }
    responses.put(
        url
        + f"?name={camera}"
        + f"&src=ffmpeg%253A{camera}%2523audio%253Dopus"
        + "&src=rtsp%253A%252F%252Ftest%253Atest%2540192.168.10.105%253A554%252F"
        + "Preview_06_sub",
        status=200,
    )
    await rest_client.streams.add(
        camera,
        [
            "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
            f"ffmpeg:{camera}#audio=opus",
        ],
    )

    responses.assert_called_once_with(
        url, method=METH_PUT, params=params, timeout=ClientTimeout(total=10)
    )


async def test_streams_add_str(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
) -> None:
    """Test add stream."""
    url = f"{URL}{_StreamClient.PATH}"
    camera = "camera.12mp_fluent"
    params = {
        "name": camera,
        "src": "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
    }
    responses.put(
        url
        + f"?name={camera}"
        + "&src=rtsp%253A%252F%252Ftest%253Atest%2540192.168.10.105%253A554%252F"
        + "Preview_06_sub",
        status=200,
    )
    await rest_client.streams.add(
        camera,
        "rtsp://test:test@192.168.10.105:554/Preview_06_sub",
    )

    responses.assert_called_once_with(
        url, method=METH_PUT, params=params, timeout=ClientTimeout(total=10)
    )


VERSION_ERR = "server version '{}' not >= 1.9.5 and < 2.0.0"


@pytest.mark.parametrize(
    ("server_version", "expected_result"),
    [
        ("0.0.0", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("0.0.0"))),
        ("1.9.4", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("1.9.4"))),
        ("1.9.5", does_not_raise()),
        ("1.9.6", does_not_raise()),
        ("2.0.0", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("2.0.0"))),
        ("BLAH", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("BLAH"))),
    ],
)
async def test_version_supported(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    server_version: str,
    expected_result: AbstractContextManager[Any],
) -> None:
    """Test validate server version."""
    payload = json.loads(load_fixture("application_info_answer.json"))
    payload["version"] = server_version
    responses.get(
        f"{URL}{_ApplicationClient.PATH}",
        status=200,
        payload=payload,
    )
    with expected_result:
        version = await rest_client.validate_server_version()
        assert version == AwesomeVersion(server_version)


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
