"""Thin async client for the Moj Elektro REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    EP_MERILNO_MESTO,
    EP_METER_READINGS,
    READINGTYPE_DAILY,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class MojElektroApiError(Exception):
    """Raised when the Moj Elektro API cannot be reached or returns an error."""


class MojElektroAuthError(MojElektroApiError):
    """Raised when the API rejects the token (HTTP 401/403)."""


class MojElektroApiClient:
    """Small wrapper around the Moj Elektro meter-reading endpoints."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        """Initialise with a shared aiohttp session and an API token."""
        self._session = session
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {"accept": "application/json", "X-API-TOKEN": self._token}

    async def _get(self, path: str, params: Any | None = None) -> Any:
        """Perform a GET request and return the decoded JSON body.

        ``params`` may be a dict or a list of ``(key, value)`` pairs (the
        meter-readings endpoint repeats the ``option`` key).
        """
        url = f"{API_BASE_URL}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    url, params=params, headers=self._headers
                ) as resp:
                    if resp.status in (401, 403):
                        raise MojElektroAuthError(
                            f"Authentication failed ({resp.status}) for {url}"
                        )
                    resp.raise_for_status()
                    return await resp.json()
        except asyncio.TimeoutError as err:
            raise MojElektroApiError(f"Timeout requesting {url}") from err
        except aiohttp.ClientError as err:
            raise MojElektroApiError(f"Error requesting {url}: {err}") from err

    async def async_get_metering_points(self, meter_id: str) -> list[dict[str, Any]]:
        """Return the metering points (``merilneTocke``) for a metering location."""
        path = EP_MERILNO_MESTO.format(meter_id=meter_id)
        data = await self._get(path)
        if isinstance(data, dict):
            return data.get("merilneTocke") or []
        return []

    async def async_validate(self, meter_id: str) -> bool:
        """Return True if the token is accepted for this metering location.

        Raises :class:`MojElektroAuthError` on a rejected token and
        :class:`MojElektroApiError` on connection problems, so the config flow
        can distinguish ``invalid_auth`` from ``cannot_connect``.
        """
        await self.async_get_metering_points(meter_id)
        return True

    async def async_get_daily_readings(
        self, usage_point: str, start: str, end: str
    ) -> list[dict[str, Any]]:
        """Return the daily cumulative-register ``intervalReadings``.

        ``start``/``end`` are ``YYYY-MM-DD`` strings. The result is the list of
        ``{timestamp, value}`` entries for the daily active-energy register, or
        an empty list when the API returns no matching block.
        """
        params = [
            ("usagePoint", usage_point),
            ("startTime", start),
            ("endTime", end),
            ("option", f"ReadingType={READINGTYPE_DAILY}"),
        ]
        data = await self._get(EP_METER_READINGS, params)
        blocks = data.get("intervalBlocks") if isinstance(data, dict) else None
        if not blocks:
            return []
        for block in blocks:
            if block.get("readingType") == READINGTYPE_DAILY:
                return block.get("intervalReadings") or []
        # Fall back to the first block if the API omits/renames the readingType.
        return blocks[0].get("intervalReadings") or []
