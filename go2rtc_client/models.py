"""Go2rtc Python models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar

from awesomeversion import AwesomeVersion
from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin
from mashumaro.types import SerializationStrategy


class _AwesomeVersionSerializer(SerializationStrategy):
    def serialize(self, value: AwesomeVersion) -> str:
        return str(value)

    def deserialize(self, value: str) -> AwesomeVersion:
        return AwesomeVersion(value)


_T = TypeVar("_T")


class _EmptyListInsteadNoneSerializer(SerializationStrategy, Generic[_T]):
    def serialize(self, value: list[_T]) -> list[_T]:
        return value

    def deserialize(self, value: list[_T] | None) -> list[_T]:
        if value is None:
            return []

        return value


@dataclass
class ApplicationInfo(DataClassORJSONMixin):
    """Application info model.

    Currently only the server version is exposed.
    """

    version: AwesomeVersion = field(
        metadata=field_options(serialization_strategy=_AwesomeVersionSerializer())
    )


@dataclass
class Streams(DataClassORJSONMixin):
    """Streams model."""

    streams: dict[str, Stream]


@dataclass
class Stream(DataClassORJSONMixin):
    """Stream model."""

    producers: list[Producer] = field(
        metadata=field_options(serialization_strategy=_EmptyListInsteadNoneSerializer())
    )


@dataclass
class Producer:
    """Producer model."""

    url: str
    media: list[str] = field(
        metadata=field_options(
            serialization_strategy=_EmptyListInsteadNoneSerializer(), alias="medias"
        )
    )

    class Config(BaseConfig):
        """Mashumaro config."""

        serialize_by_alias = True

    @classmethod
    def __pre_deserialize__(cls, d: dict[Any, Any]) -> dict[Any, Any]:
        """Pre deserialize."""
        # Ensure medias is always present
        d.setdefault("medias", [])
        return d


@dataclass
class WebRTCSdp(DataClassORJSONMixin):
    """WebRTC SDP model."""

    type: Literal["offer", "answer"]
    sdp: str


@dataclass
class WebRTCSdpOffer(WebRTCSdp):
    """WebRTC SDP offer model."""

    type: Literal["offer"] = field(default="offer", init=False)


@dataclass
class WebRTCSdpAnswer(WebRTCSdp):
    """WebRTC SDP answer model."""

    type: Literal["answer"] = field(default="answer", init=False)
