"""Go2rtc websokcet messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin
from mashumaro.config import BaseConfig
from mashumaro.types import Discriminator


@dataclass(frozen=True)
class BaseMessage(DataClassORJSONMixin):
    """Base message class."""

    TYPE: ClassVar[str]

    class Config(BaseConfig):
        """Config for BaseMessage."""

        serialize_by_alias = True
        discriminator = Discriminator(
            field="type",
            include_subtypes=True,
            variant_tagger_fn=lambda cls: cls.TYPE,
        )

    def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
        # ClassVar will not serialize by default
        d["type"] = self.TYPE
        return d


@dataclass(frozen=True)
class WebRTCCandidate(BaseMessage):
    """WebRTC ICE candidate message."""

    TYPE = "webrtc/candidate"
    candidate: str = field(metadata=field_options(alias="value"))


@dataclass(frozen=True)
class WebRTCOffer(BaseMessage):
    """WebRTC offer message."""

    TYPE = "webrtc/offer"
    offer: str = field(metadata=field_options(alias="value"))


@dataclass(frozen=True)
class WebRTCAnswer(BaseMessage):
    """WebRTC answer message."""

    TYPE = "webrtc/offer"
    answer: str = field(metadata=field_options(alias="value"))
