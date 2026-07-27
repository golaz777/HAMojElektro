"""Thin async client for the Moj Elektro REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    EP_MERILNA_TOCKA,
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

    async def async_get_metering_point_detail(self, gsrn: str) -> dict[str, Any]:
        """Return the detail for one metering point (incl. ``dogovorjeneMoci``)."""
        path = EP_MERILNA_TOCKA.format(gsrn=gsrn)
        data = await self._get(path)
        return data if isinstance(data, dict) else {}

    async def async_validate(self, meter_id: str) -> bool:
        """Return True if the token is accepted for this metering location.

        Raises :class:`MojElektroAuthError` on a rejected token and
        :class:`MojElektroApiError` on connection problems, so the config flow
        can distinguish ``invalid_auth`` from ``cannot_connect``.
        """
        await self.async_get_metering_points(meter_id)
        return True

    async def async_get_meter_readings(
        self, usage_point: str, start: str, end: str, reading_types: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Return ``{reading_type: intervalReadings}`` for the given types.

        ``start``/``end`` are ``YYYY-MM-DD`` strings. One request carries all
        reading types via repeated ``option=ReadingType=...`` params. Reading
        types with no returned block map to an empty list.
        """
        params: list[tuple[str, str]] = [
            ("usagePoint", usage_point),
            ("startTime", start),
            ("endTime", end),
        ]
        params.extend(("option", f"ReadingType={rt}") for rt in reading_types)

        data = await self._get(EP_METER_READINGS, params)
        blocks = data.get("intervalBlocks") if isinstance(data, dict) else None

        result: dict[str, list[dict[str, Any]]] = {rt: [] for rt in reading_types}
        for block in blocks or []:
            rt = block.get("readingType")
            if rt in result:
                result[rt] = block.get("intervalReadings") or []
        return result

    async def async_get_daily_readings(
        self, usage_point: str, start: str, end: str
    ) -> list[dict[str, Any]]:
        """Back-compat helper: the daily A+ total register only."""
        readings = await self.async_get_meter_readings(
            usage_point, start, end, [READINGTYPE_DAILY]
        )
        return readings.get(READINGTYPE_DAILY, [])
