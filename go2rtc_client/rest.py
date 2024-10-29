"""Client library for go2rtc."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Final, Literal

from aiohttp import ClientError, ClientResponse, ClientSession
from aiohttp.client import _RequestOptions
from awesomeversion import AwesomeVersion, AwesomeVersionException
from mashumaro.codecs.basic import BasicDecoder
from mashumaro.mixins.dict import DataClassDictMixin
from yarl import URL

from .exceptions import handle_error
from .models import ApplicationInfo, Stream, WebRTCSdpAnswer, WebRTCSdpOffer

if TYPE_CHECKING:
    from collections.abc import Mapping

_LOGGER = logging.getLogger(__name__)

_API_PREFIX = "/api"
_MIN_VERSION_SUPPORTED: Final = AwesomeVersion("1.9.5")
_MIN_VERSION_UNSUPPORTED: Final = AwesomeVersion("2.0.0")


class _BaseClient:
    """Base client for go2rtc."""

    def __init__(self, websession: ClientSession, server_url: str) -> None:
        """Initialize Client."""
        self._session = websession
        self._base_url = URL(server_url)

    async def request(
        self,
        method: Literal["GET", "PUT", "POST"],
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: DataClassDictMixin | dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Make a request to the server."""
        url = self._base_url.with_path(path)
        _LOGGER.debug("request[%s] %s", method, url)
        if isinstance(data, DataClassDictMixin):
            data = data.to_dict()
        kwargs = _RequestOptions({})
        if params:
            kwargs["params"] = params
        if data:
            kwargs["json"] = data
        try:
            resp = await self._session.request(method, url, **kwargs)
        except ClientError as err:
            msg = f"Server communication failure: {err}"
            raise ClientError(msg) from err

        resp.raise_for_status()
        return resp


class _ApplicationClient:
    PATH: Final = _API_PREFIX

    def __init__(self, client: _BaseClient) -> None:
        """Initialize Client."""
        self._client = client

    async def get_info(self) -> ApplicationInfo:
        """Get application info."""
        resp = await self._client.request("GET", self.PATH)
        return ApplicationInfo.from_dict(await resp.json())


class _WebRTCClient:
    """Client for WebRTC module."""

    PATH: Final = _API_PREFIX + "/webrtc"

    def __init__(self, client: _BaseClient) -> None:
        """Initialize Client."""
        self._client = client

    async def _forward_sdp_offer(
        self, stream_name: str, offer: WebRTCSdpOffer, src_or_dst: Literal["src", "dst"]
    ) -> WebRTCSdpAnswer:
        """Forward an SDP offer to the server."""
        resp = await self._client.request(
            "POST",
            self.PATH,
            params={src_or_dst: stream_name},
            data=offer,
        )
        return WebRTCSdpAnswer.from_dict(await resp.json())

    @handle_error
    async def forward_whep_sdp_offer(
        self, source_name: str, offer: WebRTCSdpOffer
    ) -> WebRTCSdpAnswer:
        """Forward an WHEP SDP offer to the server."""
        return await self._forward_sdp_offer(
            source_name,
            offer,
            "src",
        )


_GET_STREAMS_DECODER = BasicDecoder(dict[str, Stream])


class _StreamClient:
    PATH: Final = _API_PREFIX + "/streams"

    def __init__(self, client: _BaseClient) -> None:
        """Initialize Client."""
        self._client = client

    @handle_error
    async def list(self) -> dict[str, Stream]:
        """List streams registered with the server."""
        resp = await self._client.request("GET", self.PATH)
        return _GET_STREAMS_DECODER.decode(await resp.json())

    @handle_error
    async def add(self, name: str, source: str) -> None:
        """Add a stream to the server."""
        await self._client.request(
            "PUT",
            self.PATH,
            params={"name": name, "src": [source, f"ffmpeg:{name}#audio=opus"]},
        )


class Go2RtcRestClient:
    """Rest client for go2rtc server."""

    def __init__(self, websession: ClientSession, server_url: str) -> None:
        """Initialize Client."""
        self._client = _BaseClient(websession, server_url)
        self.application: Final = _ApplicationClient(self._client)
        self.streams: Final = _StreamClient(self._client)
        self.webrtc: Final = _WebRTCClient(self._client)

    async def validate_server_version(self) -> bool:
        """Validate the server version is compatible."""
        application_info = await self.application.get_info()
        try:
            return (
                _MIN_VERSION_SUPPORTED
                <= application_info.version
                < _MIN_VERSION_UNSUPPORTED
            )
        except AwesomeVersionException:
            _LOGGER.exception(
                "Invalid version received from server: %s", application_info.version
            )
            return False
