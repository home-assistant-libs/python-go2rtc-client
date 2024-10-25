"""Go2rtc client exceptions."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from mashumaro.exceptions import (
    ExtraKeysError,
    InvalidFieldValue,
    MissingDiscriminatorError,
    MissingField,
    SuitableVariantNotFoundError,
    UnserializableDataError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


class Go2RtcClientError(Exception):
    """Base exception for go2rtc client."""


def handle_error[**_P, _R](
    func: Callable[_P, Coroutine[Any, Any, _R]],
) -> Callable[_P, Coroutine[Any, Any, _R]]:
    """Wrap aiohttp and mashumaro errors."""

    @wraps(func)
    async def _func(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return await func(*args, **kwargs)
        except (
            ClientError,
            ExtraKeysError,
            InvalidFieldValue,
            MissingDiscriminatorError,
            MissingField,
            SuitableVariantNotFoundError,
            UnserializableDataError,
        ) as exc:
            raise Go2RtcClientError from exc

    return _func
