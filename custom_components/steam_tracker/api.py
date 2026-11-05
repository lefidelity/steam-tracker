"""Validate Steam player access and briefly share successful account summaries."""

from __future__ import annotations

from concurrent.futures import Future
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import requests


API_PLAYER_SUMMARIES = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
PLAYER_SUMMARY_CACHE_SECONDS = 15


class SteamAuthError(Exception):
    """Steam rejected access to the player-summary endpoint."""


class SteamConnectionError(Exception):
    """Steam could not be reached or returned an unsuccessful HTTP status."""


class SteamResponseError(Exception):
    """Steam returned unreadable or inconsistent player data."""


class SteamAccountNotFound(Exception):
    """Steam returned no account for the requested ID."""


@dataclass(frozen=True)
class PlayerSummaryResult:
    """Validated player data with the time it was actually fetched."""

    player: dict
    fetched_at: str


class SteamPlayerSummaryCache:
    """Share one account's summary across synchronous sensor update workers."""

    def __init__(self, api_key: str, steam_id: str) -> None:
        self._api_key = api_key
        self._steam_id = steam_id
        self._lock = Lock()
        self._result: PlayerSummaryResult | None = None
        self._expires_at = 0.0
        self._in_flight: Future[PlayerSummaryResult] | None = None

    def get(self) -> PlayerSummaryResult:
        """Reuse fresh data or join a pending fetch, without caching failures."""
        with self._lock:
            if self._result is not None and monotonic() < self._expires_at:
                return deepcopy(self._result)
            pending = self._in_flight
            if pending is None:
                fetch = True
                self._result = None
                pending = Future()
                self._in_flight = pending
            else:
                fetch = False

        if not fetch:
            return deepcopy(pending.result())

        try:
            player = fetch_player_summary(self._api_key, self._steam_id)
            result = PlayerSummaryResult(player, datetime.now(timezone.utc).isoformat())
        except Exception as error:
            with self._lock:
                self._in_flight = None
                pending.set_exception(error)
            raise

        with self._lock:
            if type(player.get("personastate")) is int and (
                not player.get("gameextrainfo") or player.get("gameid")
            ):
                self._result = result
                self._expires_at = monotonic() + PLAYER_SUMMARY_CACHE_SECONDS
            self._in_flight = None
            pending.set_result(result)
        return deepcopy(result)


def fetch_player_summary(api_key: str, steam_id: str) -> dict:
    """Fetch one account, keeping the API key out of the request URL."""
    try:
        response = requests.get(
            API_PLAYER_SUMMARIES,
            params={"steamids": steam_id},
            headers={"x-webapi-key": api_key},
            timeout=10,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise SteamConnectionError from None

    if response.status_code in (401, 403):
        raise SteamAuthError
    if response.status_code != 200:
        raise SteamConnectionError

    try:
        payload = response.json()
    except ValueError:
        raise SteamResponseError from None
    data = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or data.get("error") or data.get("success") is False:
        raise SteamResponseError
    players = data.get("players")
    if not isinstance(players, list):
        raise SteamResponseError
    if not players:
        raise SteamAccountNotFound
    if len(players) != 1 or not isinstance(players[0], dict):
        raise SteamResponseError
    if players[0].get("steamid") != steam_id:
        raise SteamResponseError
    return players[0]
