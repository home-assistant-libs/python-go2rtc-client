"""Tests for the Go2RtcWsClient class."""

import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
import logging
from unittest.mock import AsyncMock

from aiohttp import (
    ClientError,
    RequestInfo,
    WSMessage,
    WSMsgType,
    WSServerHandshakeError,
    web,
)
from aiohttp.test_utils import TestClient, TestServer as AioHttpTestServer
from aiohttp.web import WebSocketResponse
from multidict import CIMultiDict, CIMultiDictProxy
import pytest
from webrtc_models import RTCIceServer
from yarl import URL

from go2rtc_client.exceptions import Go2RtcClientError
from go2rtc_client.ws import (
    Go2RtcWsClient,
    ReceiveMessages,
    SendMessages,
    WebRTCAnswer,
    WebRTCCandidate,
    WebRTCOffer,
)


class TestServer:
    """Test server."""

    __test__ = False

    def __init__(self) -> None:
        """Initialize the test server."""
        self.server: AioHttpTestServer
        self.send_message: Callable[[str], Coroutine[None, None, None]]
        self.on_message: Callable[[WSMessage], None] = lambda _: None

    async def __aenter__(self) -> "TestServer":
        """Start the test server."""

        async def websocket_handler(request: web.Request) -> WebSocketResponse:
            ws = web.WebSocketResponse()
            await ws.prepare(request)

            async def send_message(message: str) -> None:
                await ws.send_str(message)

            self.send_message = send_message

            async for msg in ws:
                self.on_message(msg)

            return ws

        app = web.Application()
        app.router.add_get("/api/ws", websocket_handler)
        self.server = AioHttpTestServer(app)
        await self.server.start_server()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Close the test server."""
        await self.server.close()


@pytest.fixture
async def server() -> AsyncGenerator[TestServer, None]:
    """Fixture to create a WebSocket test server."""
    async with TestServer() as server:
        yield server


# Fixture to create the Go2RtcWsClient with type hints
@pytest.fixture
async def ws_client(
    server: TestServer,
) -> AsyncGenerator[Go2RtcWsClient, None]:
    """Fixture to create and return the Go2RtcWsClient."""
    async with (
        TestClient(server.server).session as session,
    ):
        client = Go2RtcWsClient(
            session, str(server.server.make_url("/")), source="source"
        )
        yield client
        await client.close()


@pytest.fixture
async def ws_client_connected(ws_client: Go2RtcWsClient) -> Go2RtcWsClient:
    """Fixture to connect client."""
    await ws_client.connect()
    return ws_client


async def test_connect(ws_client: Go2RtcWsClient) -> None:
    """Test successful connection using TestServer."""
    await ws_client.connect()

    assert ws_client.connected


async def test_connect_parallel(server: TestServer) -> None:
    """Test calling connection in parallel works."""
    async with (
        TestClient(server.server).session as session,
    ):
        client = Go2RtcWsClient(
            session, str(server.server.make_url("/")), source="source"
        )
        await asyncio.gather(client.connect(), client.connect())

        assert client.connected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (WebRTCCandidate("test"), '{"value":"test","type":"webrtc/candidate"}'),
        (
            WebRTCOffer("test", []),
            '{"value":{"sdp":"test","ice_servers":[],"type":"offer"},"type":"webrtc"}',
        ),
        (
            WebRTCOffer("test", [RTCIceServer("url")]),
            '{"value":{"sdp":"test","ice_servers":[{"urls":["url"]}],"type":"offer"},"type":"webrtc"}',
        ),
        (
            WebRTCOffer("test", [RTCIceServer(["url1", "url2"])]),
            '{"value":{"sdp":"test","ice_servers":[{"urls":["url1","url2"]}],"type":"offer"},"type":"webrtc"}',
        ),
    ],
)
async def test_send(
    ws_client: Go2RtcWsClient, server: TestServer, message: SendMessages, expected: str
) -> None:
    """Test sending a message through the WebSocket."""
    received_message = None

    def on_message(msg: WSMessage) -> None:
        nonlocal received_message
        received_message = msg.data

    server.on_message = on_message

    await ws_client.send(message)
    await asyncio.sleep(0.1)
    assert received_message == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ('{"value":"test","type":"webrtc/candidate"}', WebRTCCandidate("test")),
        (
            '{"value":{"type":"answer", "sdp":"test"},"type":"webrtc"}',
            WebRTCAnswer("test"),
        ),
    ],
)
async def test_receive(
    ws_client_connected: Go2RtcWsClient,
    server: TestServer,
    message: str,
    expected: ReceiveMessages,
) -> None:
    """Test receiving a message through the WebSocket."""
    received_message = None

    def on_message(message: ReceiveMessages) -> None:
        nonlocal received_message
        received_message = message

    ws_client_connected.subscribe(on_message)

    await server.send_message(message)
    await asyncio.sleep(0.1)

    assert received_message == expected


async def test_close(ws_client_connected: Go2RtcWsClient) -> None:
    """Test closing the WebSocket connection."""
    assert ws_client_connected.connected

    await ws_client_connected.close()

    assert not ws_client_connected.connected


async def test_source_and_destionation_should_raise(server: TestServer) -> None:
    """Test source and destination cannot be set at the same time."""
    async with TestClient(server.server).session as session:
        with pytest.raises(
            ValueError, match="Source and destination cannot be set at the same time"
        ):
            Go2RtcWsClient(
                session,
                str(server.server.make_url("/")),
                source="source",
                destination="destination",
            )


async def test_missing_params_should_raise(server: TestServer) -> None:
    """Test source or destination must be set."""
    async with TestClient(server.server).session as session:
        with pytest.raises(ValueError, match="Source or destination must be set"):
            Go2RtcWsClient(
                session,
                str(server.server.make_url("/")),
            )


@pytest.mark.parametrize(
    "exception",
    [
        WSServerHandshakeError(
            RequestInfo(URL(), "GET", CIMultiDictProxy(CIMultiDict()), URL()), ()
        ),
        ClientError,
    ],
)
async def test_error_on_connect(
    ws_client: Go2RtcWsClient, exception: Exception
) -> None:
    """Test error on connect."""
    ws_client._session.ws_connect = AsyncMock(side_effect=exception)  # type: ignore[method-assign] # pylint: disable=protected-access

    with pytest.raises(Go2RtcClientError):
        await ws_client.connect()


@pytest.mark.usefixtures("ws_client_connected")
async def test_receive_invalid_message(
    caplog: pytest.LogCaptureFixture,
    server: TestServer,
) -> None:
    """Test receiving an invalid message from the WebSocket server."""
    # Simulate receiving an invalid message
    await server.send_message("invalid json")
    await asyncio.sleep(0.1)

    assert caplog.record_tuples == [
        (
            "go2rtc_client.ws.client",
            logging.ERROR,
            "Invalid message received: invalid json",
        )
    ]


async def test_subscribe_unsubscribe(ws_client: Go2RtcWsClient) -> None:
    """Test subscribe and unsubscribe functionality."""
    # pylint: disable=protected-access
    assert ws_client._subscribers == []

    def on_message(_: ReceiveMessages) -> None:
        pass

    unsub = ws_client.subscribe(on_message)

    assert ws_client._subscribers == [on_message]

    unsub()

    assert ws_client._subscribers == []


async def test_subscriber_raised(
    ws_client_connected: Go2RtcWsClient,
    server: TestServer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test any exception raised by any subscriber will be handled."""

    def on_message_raise(_: ReceiveMessages) -> None:
        raise ValueError

    ws_client_connected.subscribe(on_message_raise)

    received_message = None

    def on_message(message: ReceiveMessages) -> None:
        nonlocal received_message
        received_message = message

    ws_client_connected.subscribe(on_message)

    message = WebRTCCandidate("test")
    await server.send_message(message.to_json())
    await asyncio.sleep(0.1)

    assert received_message == message
    assert caplog.record_tuples == [
        (
            "go2rtc_client.ws.client",
            logging.ERROR,
            "Error on subscriber callback",
        )
    ]


@pytest.mark.parametrize(
    ("message", "record"),
    [
        (
            WSMessage(WSMsgType.BINARY, b"bytes", None),
            (
                "go2rtc_client.ws.client",
                logging.WARNING,
                (
                    "Received unknown message: WSMessage(type=<WSMsgType.BINARY: 2>,"
                    " data=b'bytes', extra=None)"
                ),
            ),
        ),
        (
            WSMessage(WSMsgType.ERROR, "error", None),
            ("go2rtc_client.ws.client", logging.ERROR, "Error received: error"),
        ),
        (
            WSMessage(
                WSMsgType.TEXT,
                '{"value":{"sdp":"test","ice_servers":[],"type":"offer"},"type":"webrtc"}',
                None,
            ),
            (
                "go2rtc_client.ws.client",
                logging.ERROR,
                "Received unexpected message: WebRTCOffer(sdp='test', ice_servers=[])",
            ),
        ),
    ],
)
async def test_unexpected_messages(
    caplog: pytest.LogCaptureFixture,
    ws_client: Go2RtcWsClient,
    message: WSMessage,
    record: tuple[str, int, str],
) -> None:
    """Test unexpected messages."""
    client = AsyncMock()
    client.return_value.closed = False
    ws_client._session.ws_connect = client  # type: ignore[method-assign] # pylint: disable=protected-access

    async def receive() -> WSMessage:
        nonlocal client
        client.return_value.closed = True

        return message

    client.return_value.receive.side_effect = receive

    await ws_client.connect()
    await asyncio.sleep(0.1)

    assert caplog.record_tuples == [record]
