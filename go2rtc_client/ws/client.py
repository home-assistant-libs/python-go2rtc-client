"""Websocket client for go2rtc server."""

import asyncio
import logging
from typing import TYPE_CHECKING
from collections.abc import Callable
from urllib.parse import urljoin
from aiohttp import (
    ClientError,
    ClientSession,
    ClientWebSocketResponse,
    WSMsgType,
    WSServerHandshakeError,
)


from go2rtc_client.exceptions import Go2RtcClientError
from go2rtc_client.ws.messages import BaseMessage

_LOGGER = logging.getLogger(__name__)


class Go2RtcWsClient:
    """Websocket client for go2rtc server."""

    def __init__(
        self,
        session: ClientSession,
        server_url: str,
        *,
        source: str | None = None,
        destination: str | None = None,
    ) -> None:
        """Initialize Client."""
        if source:
            if destination:
                raise ValueError(
                    "source and destination cannot be set at the same time"
                )
            params = {"src": source}
        elif destination:
            params = {"dst": destination}
        else:
            raise ValueError("source or destination must be set")

        self._server_url = server_url
        self._session = session
        self._params = params
        self._client: ClientWebSocketResponse | None = None
        self._rx_task: asyncio.Task[None] | None = None
        self._subscribers: list[Callable[[BaseMessage], None]] = []

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self._client is not None and not self._client.closed

    async def connect(self) -> None:
        """Connect to device."""
        if self.connected:
            return

        _LOGGER.debug("Trying to connect to %s", self._server_url)
        try:
            self._client = await self._session.ws_connect(
                urljoin(self._server_url, "/api/ws"), params=self._params
            )
        except (
            WSServerHandshakeError,
            ClientError,
        ) as err:
            raise Go2RtcClientError(err) from err

        self._rx_task = asyncio.create_task(self._receive_messages())
        _LOGGER.info("Connected to %s", self._server_url)

    async def close(self) -> None:
        """Close connection."""
        if self.connected:
            if TYPE_CHECKING:
                assert self._client is not None
            client = self._client
            self._client = None
            await client.close()

    async def send(self, message: BaseMessage) -> None:
        """Send a message."""
        if not self.connected:
            await self.connect()

        if TYPE_CHECKING:
            assert self._client is not None

        await self._client.send_str(message.to_json())

    async def _receive_messages(self) -> None:
        """Receive messages."""

        if TYPE_CHECKING:
            assert self._client

        try:
            while self.connected:
                msg = await self._client.receive()
                match msg.type:
                    case WSMsgType.CLOSE:
                        break
                    case WSMsgType.CLOSED:
                        break
                    case WSMsgType.CLOSING:
                        break
                    case WSMsgType.ERROR:
                        _LOGGER.error("Error received: %s", msg.data)
                        continue
                    case WSMsgType.TEXT:
                        try:
                            message = BaseMessage.from_json(msg.data)
                        except Exception:  # pylint: disable=broad-except
                            _LOGGER.exception("Invalid message received: %s", msg.data)
                            continue

                        for subscriber in self._subscribers:
                            try:
                                subscriber(message)
                            except Exception:  # pylint: disable=broad-except
                                _LOGGER.exception("Error on subscriber callback")
                    case _:
                        _LOGGER.warning("Received unknown message: %s", msg)
                        continue
        except Exception:
            _LOGGER.exception("Unexpected error while receiving message")
            raise
        finally:
            _LOGGER.debug(
                "Websocket client connection from %s closed", self._server_url
            )

            if self.connected:
                await self.close()

    def subscribe(self, callback: Callable[[BaseMessage], None]) -> Callable[[], None]:
        """Subscribe to messages."""

        def _unsubscribe() -> None:
            self._subscribers.remove(callback)

        self._subscribers.append(callback)
        return _unsubscribe
