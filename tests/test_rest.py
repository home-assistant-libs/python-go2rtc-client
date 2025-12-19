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
from go2rtc_client.rest import (
    _API_PREFIX,
    _ApplicationClient,
    _PreloadClient,
    _SchemesClient,
    _StreamClient,
    _WebRTCClient,
)

from . import URL, load_fixture_bytes, load_fixture_str

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
        body=load_fixture_str("application_info_answer.json"),
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
        body=load_fixture_str(filename),
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


VERSION_ERR = "server version '{}' not >= 1.9.13 and < 2.0.0"


@pytest.mark.parametrize(
    ("server_version", "expected_result"),
    [
        ("0.0.0", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("0.0.0"))),
        ("1.9.5", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("1.9.5"))),
        ("1.9.6", pytest.raises(Go2RtcVersionError, match=VERSION_ERR.format("1.9.6"))),
        ("1.9.13", does_not_raise()),
        ("1.9.14", does_not_raise()),
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
    payload = json.loads(load_fixture_str("application_info_answer.json"))
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
        body=load_fixture_str("webrtc_answer.json"),
    )
    resp = await rest_client.webrtc.forward_whep_sdp_offer(
        camera,
        WebRTCSdpOffer("v=0..."),
    )
    assert resp == snapshot


@pytest.mark.parametrize(
    ("height", "width", "additional_params"),
    [
        (None, None, ""),
        (100, None, "&height=100"),
        (None, 200, "&width=200"),
        (100, 200, "&height=100&width=200"),
    ],
    ids=[
        "No height and no width",
        "Only height",
        "Only width",
        "Height and width",
    ],
)
async def test_get_jpeg_snapshot(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    height: int | None,
    width: int | None,
    additional_params: str,
) -> None:
    """Test getting a jpeg snapshot."""
    camera = "camera.12mp_fluent"
    image_bytes = load_fixture_bytes("snapshot.jpg")
    responses.get(
        f"{URL}{_API_PREFIX}/frame.jpeg?src={camera}{additional_params}",
        status=200,
        body=image_bytes,
    )
    resp = await rest_client.get_jpeg_snapshot(camera, width, height)
    assert isinstance(resp, bytes)

    assert resp == image_bytes


async def test_schemes(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    snapshot: SnapshotAssertion,
) -> None:
    """Test schemes."""
    responses.get(
        f"{URL}{_SchemesClient.PATH}",
        status=200,
        body=json.dumps(["webrtc", "exec", "ffmpeg", "rtsp", "rtsps", "rtspx"]),
    )
    resp = await rest_client.schemes.list()
    assert resp == snapshot


@pytest.mark.parametrize(
    "filename",
    ["preload_list_one.json", "streams_none.json"],
    ids=[
        "one stream preloaded",
        "no stream preloaded",
    ],
)
async def test_preload_list(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    snapshot: SnapshotAssertion,
    filename: str,
) -> None:
    """Test preload list."""
    responses.get(
        f"{URL}{_PreloadClient.PATH}",
        status=200,
        body=load_fixture_str(filename),
    )
    resp = await rest_client.preload.list()
    assert resp == snapshot


async def test_preload_enable_no_filters(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
) -> None:
    """Test enable preload without codec filters."""
    url = f"{URL}{_PreloadClient.PATH}"
    camera = "camera.12mp_fluent"
    params = {"src": camera}
    responses.put(url + f"?src={camera}", status=200)
    await rest_client.preload.enable(camera)

    responses.assert_called_once_with(
        url, method=METH_PUT, params=params, timeout=ClientTimeout(total=10)
    )


@pytest.mark.parametrize(
    ("video_codecs", "audio_codecs", "microphone_codecs", "expected_params"),
    [
        (
            ["h264"],
            None,
            None,
            {"src": "camera.12mp_fluent", "video_codec_filter": "h264"},
        ),
        (
            None,
            ["opus"],
            None,
            {"src": "camera.12mp_fluent", "audio_codec_filter": "opus"},
        ),
        (
            None,
            None,
            ["pcmu"],
            {"src": "camera.12mp_fluent", "microphone_codec_filter": "pcmu"},
        ),
        (
            ["h264", "h265"],
            ["opus", "pcma"],
            ["pcmu"],
            {
                "src": "camera.12mp_fluent",
                "video_codec_filter": "h264,h265",
                "audio_codec_filter": "opus,pcma",
                "microphone_codec_filter": "pcmu",
            },
        ),
    ],
    ids=[
        "video filter only",
        "audio filter only",
        "microphone filter only",
        "all filters",
    ],
)
async def test_preload_enable_with_filters(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
    video_codecs: list[str] | None,
    audio_codecs: list[str] | None,
    microphone_codecs: list[str] | None,
    expected_params: dict[str, str],
) -> None:
    """Test enable preload with codec filters."""
    url = f"{URL}{_PreloadClient.PATH}"
    camera = "camera.12mp_fluent"

    # Build the expected URL query string
    query_parts = [f"src={camera}"]
    if video_codecs:
        query_parts.append(f"video_codec_filter={','.join(video_codecs)}")
    if audio_codecs:
        query_parts.append(f"audio_codec_filter={','.join(audio_codecs)}")
    if microphone_codecs:
        query_parts.append(f"microphone_codec_filter={','.join(microphone_codecs)}")

    responses.put(url + "?" + "&".join(query_parts), status=200)
    await rest_client.preload.enable(
        camera,
        video_codec_filter=video_codecs,
        audio_codec_filter=audio_codecs,
        microphone_codec_filter=microphone_codecs,
    )

    responses.assert_called_once_with(
        url, method=METH_PUT, params=expected_params, timeout=ClientTimeout(total=10)
    )


async def test_preload_disable(
    responses: aioresponses,
    rest_client: Go2RtcRestClient,
) -> None:
    """Test disable preload."""
    url = f"{URL}{_PreloadClient.PATH}"
    camera = "camera.12mp_fluent"
    params = {"src": camera}
    responses.delete(url + f"?src={camera}", status=200)
    await rest_client.preload.disable(camera)

    responses.assert_called_once_with(
        url, method="DELETE", params=params, timeout=ClientTimeout(total=10)
    )
