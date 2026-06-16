"""
Lightweight HTTP mock utility replacing aioresponses.

aioresponses 0.7.8 is incompatible with aiohttp >= 3.14 because it
instantiates ClientResponse directly with kwargs that no longer match
the updated constructor signature.  This module provides a minimal
drop-in replacement that patches ``aiohttp.ClientSession.get`` with
simple objects that have no dependency on aiohttp internals.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Protocol, Self
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Callable

_HTTP_ERROR_THRESHOLD = 400


class _PatcherProtocol(Protocol):
    """Minimal interface for unittest.mock patch objects."""

    def start(self) -> object:
        """Activate the patch."""
        ...

    def stop(self) -> None:
        """Deactivate the patch."""
        ...


class _MockResponse:
    """Minimal async context manager mimicking an aiohttp response."""

    def __init__(self, status: int, payload: object) -> None:
        """Initialise with HTTP status and response payload."""
        self.status = status
        self.headers: dict[str, str] = {}
        self._payload = payload

    async def json(self) -> object:
        """Return the registered payload."""
        return self._payload

    def raise_for_status(self) -> None:
        """Raise RuntimeError for 4xx/5xx responses."""
        if self.status >= _HTTP_ERROR_THRESHOLD:
            msg = f"HTTP Error {self.status}"
            raise RuntimeError(msg)

    async def __aenter__(self) -> Self:
        """Return self as the context manager value."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """No-op exit."""


class MockHTTP:
    """
    Context manager that intercepts ``aiohttp.ClientSession.get`` calls.

    Usage mirrors the basic aioresponses API::

        with MockHTTP() as mocked:
            mocked.get(url, status=200, payload=data)
            # ... run code that calls aiohttp ...
    """

    def __init__(self) -> None:
        """Initialise with an empty response registry."""
        self._responses: dict[str, list[tuple[int, object]]] = {}
        self._patcher: _PatcherProtocol | None = None

    def get(
        self,
        url: str,
        *,
        status: int = 200,
        payload: object = None,
    ) -> None:
        """Register a GET response for *url*."""
        if url not in self._responses:
            self._responses[url] = []
        self._responses[url].append((status, payload))

    def _get_side_effect(self, url: str, **_kwargs: object) -> _MockResponse:
        if url not in self._responses or not self._responses[url]:
            msg = f"Unexpected GET request to {url!r}"
            raise AssertionError(msg)
        status, payload = self._responses[url].pop(0)
        return _MockResponse(status, payload)

    def __enter__(self) -> Self:
        """Start intercepting HTTP GET requests."""
        self._patcher = patch(
            "aiohttp.ClientSession.get",
            side_effect=self._get_side_effect,
        )
        self._patcher.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Stop intercepting HTTP GET requests."""
        if self._patcher is not None:
            self._patcher.stop()


def mock_http() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Return a decorator that injects a MockHTTP instance into the test.

    Mirrors the ``@aioresponses()`` decorator API::

        @mock_http()
        def test_something(self, mocked: MockHTTP) -> None:
            mocked.get(url, status=200, payload=data)
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            with MockHTTP() as mocked:
                return func(*args, mocked, **kwargs)

        return wrapper

    return decorator
