"""Integration to get Steam account information."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import (
    API_PLAYER_SUMMARIES,
    SteamAuthError,
    SteamPlayerSummaryCache,
    fetch_player_summary,
)
from .const import CONF_STEAM_ID, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Slow library scans must not delay status updates.
PARALLEL_UPDATES = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_STEAM_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

API_URL = API_PLAYER_SUMMARIES


class _SteamAchievementError(Exception):
    """Keep trusted request context with an achievement failure."""

    def __init__(self, error: Exception, operation: str, appid: int) -> None:
        super().__init__("Steam achievement request failed")
        self.error = error
        self.operation = operation
        self.appid = appid


def _log_api_error(
    message: str, error: Exception, *, operation: str | None = None
) -> None:
    """Log an API failure without exposing request URLs or credentials."""
    if isinstance(error, _SteamAchievementError):
        operation = error.operation
        if type(error.appid) is int and error.appid > 0:
            operation = f"{operation}, appid={error.appid}"
        error = error.error
    if operation is not None:
        message = f"{message} [{operation}]"
    error_type = type(error).__name__
    if isinstance(error, requests.RequestException) and error.response is not None:
        _LOGGER.error(
            "%s (%s, HTTP %s)", message, error_type, error.response.status_code
        )
    else:
        _LOGGER.error("%s (%s)", message, error_type)


def _response_data(response: requests.Response, key: str = "response") -> dict:
    """Read a successful Steam response without substituting missing data."""
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get(key), dict):
        raise ValueError("Missing or invalid Steam response")
    data = payload[key]
    if data.get("success") is False or data.get("error"):
        raise ValueError("Steam response indicates a failure")
    return data


def _response_list(data: dict, key: str, count_key: str | None = None) -> list[dict]:
    """Distinguish an explicitly empty list from unavailable list data."""
    count = data.get(count_key) if count_key is not None else None
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError("Invalid Steam result count")
    items = data.get(key, [] if count == 0 else None)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError("Missing or invalid Steam list data")
    if count is not None and (count < len(items) or (count > 0 and not items)):
        raise ValueError("Incomplete Steam list data")
    return items


def _validate_achievement_games(games: list[dict]) -> None:
    """Require distinct, valid app IDs before fetching achievement data."""
    appids = [game.get("appid") for game in games]
    if any(type(appid) is not int or appid <= 0 for appid in appids):
        raise ValueError("Missing or invalid Steam app ID")
    if len(set(appids)) != len(appids):
        raise ValueError("Duplicate Steam app IDs")


def _achievement_names(achievements: list[dict], key: str) -> set[str]:
    """Validate achievement identifiers without counting duplicate records."""
    names = [achievement.get(key) for achievement in achievements]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Missing or invalid Steam achievement identifier")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate Steam achievement identifiers")
    return set(names)


def _player_achievements(response: requests.Response) -> dict[str, int] | None:
    """Read confirmed progress, or require a schema for ambiguous missing stats."""
    if response.status_code not in (200, 400):
        response.raise_for_status()
        raise ValueError("Unexpected Steam achievement response status")
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(
        payload.get("playerstats"), dict
    ):
        raise ValueError("Missing or invalid Steam player stats")
    data = payload["playerstats"]
    if (
        data.get("success") is False
        and data.get("error") == "Requested app has no stats"
        and data.get("achievements") in (None, [])
    ):
        return None
    response.raise_for_status()
    if data.get("success") is not True or data.get("error"):
        raise ValueError("Steam player achievements are unavailable")
    if "achievements" not in data:
        return None
    achievements = _response_list(data, "achievements")
    if not achievements:
        return None
    _achievement_names(achievements, "apiname")
    if any(
        type(achievement.get("achieved")) is not int
        or achievement["achieved"] not in (0, 1)
        for achievement in achievements
    ):
        raise ValueError("Missing or invalid Steam achievement progress")
    return {
        achievement["apiname"]: achievement["achieved"]
        for achievement in achievements
    }


def _schema_achievements(response: requests.Response) -> set[str]:
    """Read a valid game schema, including games with no achievements."""
    data = _response_data(response, "game")
    stats = data.get("availableGameStats", {})
    if not isinstance(stats, dict):
        raise ValueError("Steam achievement schema is unavailable")
    achievements = (
        _response_list(stats, "achievements") if "achievements" in stats else []
    )
    return _achievement_names(achievements, "name")


def _library_statistics(games: list[dict]) -> dict:
    """Calculate library usage from exact lifetime minutes already fetched."""
    distribution = {
        "unplayed": 0,
        "under_1_hour": 0,
        "1_to_10_hours": 0,
        "10_to_50_hours": 0,
        "50_hours_or_more": 0,
    }
    unplayed_games = []
    for game in games:
        minutes = game.get("playtime_forever")
        if type(minutes) is not int or minutes < 0:
            raise ValueError("Missing or invalid Steam playtime minutes")
        if minutes == 0:
            bucket = "unplayed"
            unplayed_games.append({"appid": game["appid"], "name": game.get("name")})
        elif minutes < 60:
            bucket = "under_1_hour"
        elif minutes < 600:
            bucket = "1_to_10_hours"
        elif minutes < 3000:
            bucket = "10_to_50_hours"
        else:
            bucket = "50_hours_or_more"
        distribution[bucket] += 1

    played_count = len(games) - len(unplayed_games)
    return {
        "played_game_count": played_count,
        "unplayed_game_count": len(unplayed_games),
        "unplayed_games": sorted(unplayed_games, key=lambda game: game.get("name") or ""),
        "played_percentage": round(played_count / len(games) * 100, 1) if games else 0,
        "playtime_distribution": distribution,
    }


def _global_achievement_statistics(games: list[dict]) -> dict:
    """Summarize a complete scan, using exact counts for completion groups."""
    distribution = dict.fromkeys(
        ("not_started", "under_25", "25_to_50", "50_to_75", "75_to_100", "complete"),
        0,
    )
    achievement_games = [game for game in games if game["total"] > 0]
    unlocked = sum(game["unlocked"] for game in achievement_games)
    possible = sum(game["total"] for game in achievement_games)
    for game in achievement_games:
        done, total = game["unlocked"], game["total"]
        if done == 0:
            group = "not_started"
        elif done == total:
            group = "complete"
        elif done * 4 < total:
            group = "under_25"
        elif done * 2 < total:
            group = "25_to_50"
        elif done * 4 < total * 3:
            group = "50_to_75"
        else:
            group = "75_to_100"
        distribution[group] += 1

    candidates = sorted(
        (game for game in achievement_games if game["unlocked"] < game["total"]),
        key=lambda game: (
            game["total"] - game["unlocked"],
            -game["unlocked"] / game["total"],
            (game.get("name") or "").casefold(),
            game["appid"],
        ),
    )[:5]
    return {
        "achievements_total": unlocked,
        "achievements_possible": possible,
        "perfect_games": distribution["complete"],
        "avg_completion_rate": round(
            sum(game["unlocked"] / game["total"] * 100 for game in achievement_games)
            / len(achievement_games), 1
        ) if achievement_games else 0,
        "achievements_remaining": possible - unlocked,
        "overall_completion_rate": round(unlocked / possible * 100, 1) if possible else None,
        "games_with_achievements": len(achievement_games),
        "games_without_achievements": len(games) - len(achievement_games),
        "completion_distribution": distribution,
        "completion_candidates": [
            {
                **game,
                "remaining": game["total"] - game["unlocked"],
                "percent": round(game["unlocked"] / game["total"] * 100, 1),
            }
            for game in candidates
        ],
    }


def _create_entities(
    api_key: str, steam_id: str, name: str, *, use_device_name: bool = False
) -> list["SteamBaseSensor"]:
    """Create all Steam Tracker sensor entities."""
    base_name = name or DEFAULT_NAME
    prefix = "" if use_device_name else f"{base_name} "
    if base_name != DEFAULT_NAME:
        prefix += "Steam "
    player_summary_cache = SteamPlayerSummaryCache(api_key, steam_id)
    entities = [
        SteamStatusSensor(
            api_key, steam_id, f"{prefix}Status", account_name=base_name,
            player_summary_cache=player_summary_cache,
        ),
        SteamGameSensor(
            api_key, steam_id, f"{prefix}Game", account_name=base_name,
            player_summary_cache=player_summary_cache,
        ),
        SteamPlaytimeSensor(
            api_key, steam_id, f"{prefix}Playtime", account_name=base_name
        ),
        SteamProfileSensor(
            api_key, steam_id, f"{prefix}Profile", account_name=base_name
        ),
        SteamRecentGamesSensor(
            api_key, steam_id, f"{prefix}Recent", account_name=base_name
        ),
        SteamRecentAchievementsSensor(
            api_key, steam_id, f"{prefix}Recent Achievements", account_name=base_name
        ),
        SteamGlobalStatsSensor(
            api_key, steam_id, f"{prefix}Global Stats", account_name=base_name
        ),
        SteamFriendsSensor(
            api_key, steam_id, f"{prefix}Friends", account_name=base_name
        ),
    ]
    for entity in entities:
        entity._attr_has_entity_name = use_device_name
    return entities


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Steam Tracker sensors from YAML."""
    api_key = config[CONF_API_KEY]
    steam_id = config[CONF_STEAM_ID]
    name = config.get(CONF_NAME, DEFAULT_NAME)

    add_entities(_create_entities(api_key, steam_id, name))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Steam Tracker sensors from a config entry."""
    data = entry.data
    name = entry.title or data.get(CONF_NAME, DEFAULT_NAME)
    entities = _create_entities(
        data[CONF_API_KEY], data[CONF_STEAM_ID], name, use_device_name=True
    )
    async_add_entities(entities)


class SteamBaseSensor(SensorEntity):
    """Base class for Steam Tracker sensors."""

    sensor_type = "base"
    update_interval = timedelta(minutes=5)

    def __init__(
        self,
        api_key: str,
        steam_id: str,
        name: str,
        *,
        account_name: str | None = None,
        player_summary_cache: SteamPlayerSummaryCache | None = None,
    ) -> None:
        self._api_key = api_key
        self._steam_id = steam_id
        self._player_summary_cache = player_summary_cache
        self._attr_name = name
        self._attr_should_poll = False
        self._attr_available = False
        self._attr_unique_id = f"{steam_id}_{self.sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, steam_id)},
            name=account_name or DEFAULT_NAME,
            manufacturer="Valve",
            model="Steam Account",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._state = None
        self._attrs = {}

    async def async_added_to_hass(self) -> None:
        """Schedule an initial refresh and independent periodic updates."""
        await super().async_added_to_hass()
        entry = self.platform.config_entry
        if entry is None:
            initial_refresh = self.hass.async_create_background_task(
                self._async_refresh(),
                f"{self.entity_id} initial update",
                eager_start=False,
            )
        else:
            initial_refresh = entry.async_create_background_task(
                self.hass,
                self._async_refresh(),
                f"{self.entity_id} initial update",
                eager_start=False,
            )
        self.async_on_remove(initial_refresh.cancel)

        if entry is not None and entry.pref_disable_polling:
            return

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_refresh,
                self.update_interval,
                cancel_on_shutdown=True,
            )
        )

    async def _async_refresh(self, _now: datetime | None = None) -> None:
        """Refresh through Home Assistant's executor and per-entity update guard."""
        if self.hass is None:
            return
        await self.async_device_update()
        if self.hass is not None:
            self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attrs

    def _set_unavailable(self) -> None:
        """Discard stale values after a failed primary data refresh."""
        self._attr_available = False
        self._state = None
        self._attrs = {}

    def _mark_successful_update(self, fetched_at: str | None = None) -> None:
        """Use the source fetch time, or completion of this validated update."""
        self._attrs["last_successful_update"] = (
            fetched_at if fetched_at is not None else datetime.now(timezone.utc).isoformat()
        )
        self._attr_available = True

    def _achievement_progress(
        self, appid: int, *, verify_schema: bool = False
    ) -> tuple[int, int]:
        """Fetch validated counts without substituting zero for unknown progress."""
        params = {"key": self._api_key, "steamid": self._steam_id, "appid": appid}
        operation = "GetPlayerAchievements/v1"
        try:
            response = requests.get(API_ACHIEVEMENTS, params=params, timeout=10)
            # Confirm missing achievements through the schema even after HTTP 500.
            player_stats_failed = response.status_code == 500
            achievements = None if player_stats_failed else _player_achievements(response)
            if verify_schema or achievements is None:
                operation = "GetSchemaForGame/v2"
                schema_response = requests.get(
                    API_SCHEMA, params={"key": self._api_key, "appid": appid}, timeout=10
                )
                names = _schema_achievements(schema_response)
                if achievements is None:
                    if names:
                        if player_stats_failed:
                            operation = "GetPlayerAchievements/v1"
                            response.raise_for_status()
                        raise ValueError("Steam player achievement progress is unavailable")
                    return 0, 0
                if set(achievements) != names:
                    raise ValueError("Incomplete Steam player achievement data")
            return sum(achievements.values()), len(achievements)
        except Exception as error:
            raise _SteamAchievementError(error, operation, appid) from None

    def update(self):
        """Fetch data from Steam API."""
        try:
            fetched_at = None
            if self._player_summary_cache is None:
                player = fetch_player_summary(self._api_key, self._steam_id)
            else:
                summary = self._player_summary_cache.get()
                player = summary.player
                fetched_at = summary.fetched_at
            self.parse_data(player)
            self._mark_successful_update(fetched_at)
        except SteamAuthError as error:
            _log_api_error("Steam denied player-summary access", error)
            self._set_unavailable()
            if self.hass is not None:
                self.hass.loop.call_soon_threadsafe(self._async_start_reauth)
        except Exception as e:
            _log_api_error("Error fetching data from Steam", e)
            self._set_unavailable()

    @callback
    def _async_start_reauth(self) -> None:
        """Request reauthentication on the event loop for UI accounts only."""
        if self.hass is not None and (entry := self.platform.config_entry) is not None:
            entry.async_start_reauth(self.hass)


class SteamStatusSensor(SteamBaseSensor):
    """Shows online status of the player."""

    sensor_type = "status"
    update_interval = timedelta(minutes=1)
    
    def parse_data(self, data):
        if type(data.get("personastate")) is not int:
            raise ValueError("Steam player status is unavailable")
        state_map = {
            0: "Offline",
            1: "Online",
            2: "Busy",
            3: "Away",
            4: "Snooze",
            5: "Looking to trade",
            6: "Looking to play",
        }
        self._state = state_map.get(data["personastate"], "Unknown")
        self._attrs = {
            "personaname": data.get("personaname"),
            "profileurl": data.get("profileurl"),
            "avatar": data.get("avatarfull"),
            "lastlogoff": data.get("lastlogoff"),
        }


class SteamGameSensor(SteamBaseSensor):
    """Shows current game being played."""

    sensor_type = "game"
    update_interval = timedelta(minutes=2)
    
    def parse_data(self, data):
        current_game = data.get("gameextrainfo")
        if not current_game:
            if (
                data.get("communityvisibilitystate") not in (None, 3)
                or type(data.get("personastate")) is not int
            ):
                raise ValueError("Steam current game data is unavailable")
            self._state = "none"
            self._attrs = {}
            return

        if not data.get("gameid"):
            raise ValueError("Steam current game ID is unavailable")
    
        current_game_id = str(data.get("gameid"))
    
        # standard infos
        self._state = current_game
        self._attrs = {
            "gameid": current_game_id,
            "name": current_game,
            "personaname": data.get("personaname"),
            "logo": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{current_game_id}/header.jpg",
        }
    
        # get overall playtime for current game
        try:
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "include_appinfo": False,
                "include_played_free_games": True,
            }
            resp = requests.get(API_OWNED_GAMES, params=params, timeout=10)
            games = _response_list(_response_data(resp), "games", "game_count")
            for g in games:
                if str(g.get("appid")) == current_game_id:
                    hours = round(g.get("playtime_forever", 0) / 60, 1)
                    self._attrs["total_playtime_hours"] = hours
                    break
        except Exception as e:
            _log_api_error("Error fetching playtime for current game", e)


API_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

class SteamPlaytimeSensor(SteamBaseSensor):
    """Shows total playtime and top 5 games."""

    sensor_type = "playtime"
    update_interval = timedelta(hours=1)

    def update(self):
        """Fetch owned games and playtime data from Steam API."""
        try:
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "include_appinfo": True,   # liefert Namen der Spiele
                "include_played_free_games": True
            }
            response = requests.get(API_OWNED_GAMES, params=params, timeout=15)
            games = _response_list(_response_data(response), "games", "game_count")
            _validate_achievement_games(games)
            library_stats = _library_statistics(games)
            if not games:
                self._state = 0
                self._attrs = {
                    "top_5_games": [],
                    "all_games": [],
                    "game_count": 0,
                    "total_playtime_hours": 0,
                    "top_5_playtime_hours": 0,
                    "playtime_by_gameid": {},
                    "pile_of_shame_count": 0,
                    "top_5_playtime_percentage": 0,
                    **library_stats,
                }
                self._mark_successful_update()
                return

            # overall playtime in hours
            total_minutes = sum(g.get("playtime_forever", 0) for g in games)
            self._state = round(total_minutes / 60, 1)

            # top 5 games according to playtime
            top_games = sorted(
                games,
                key=lambda x: x.get("playtime_forever", 0),
                reverse=True
            )[:5]
            
            # a list of all games with playtime in hours
            all_games = [
                {
                    "appid": g["appid"],
                    "name": g.get("name"),
                    "playtime_minutes": g["playtime_forever"],
                    "hours": round(g.get("playtime_forever", 0) / 60, 1)
                }
                for g in sorted(games, key=lambda x: x.get("name", ""))
            ]
            
            pile_of_shame = [
                g for g in games if g.get("playtime_forever", 0) < 60
            ]
            
            # overall minues
            total_minutes = sum(g.get("playtime_forever", 0) for g in games)
            total_hours = round(total_minutes / 60, 1)
            
            # top 5 hours
            top_minutes = sum(g["playtime_forever"] for g in top_games)
            top_hours = round(top_minutes / 60, 1)
            
            playtime_by_gameid = {
                str(g["appid"]): round(g.get("playtime_forever", 0) / 60, 1)
                for g in games
            }
            
            top_games_list = []
            for g in top_games:
                appid = g.get("appid")
                name = g.get("name")
                hours = round(g.get("playtime_forever", 0) / 60, 1)
            
                unlocked, total, percent = None, None, None
            
                try:
                    unlocked, total = self._achievement_progress(appid)
                    if total > 0:
                        percent = round((unlocked / total) * 100, 1)
                except Exception as e:
                    _log_api_error("Error fetching top-game achievement data", e)
            
                top_games_list.append({
                    "appid": appid,
                    "name": name,
                    "hours": hours,
                    "logo": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                    "achievements_unlocked": unlocked,
                    "achievements_total": total,
                    "achievements_percent": percent,
                })

            
            self._state = total_hours  # overall playtime as state in hours
            self._attrs = {
                "top_5_games": top_games_list,
                "all_games": all_games,
                "game_count": len(games),
                "total_playtime_hours": total_hours,
                "top_5_playtime_hours": top_hours,
                "playtime_by_gameid": playtime_by_gameid,
                "pile_of_shame_count": len(pile_of_shame),
                "top_5_playtime_percentage": (
                    round(top_minutes / total_minutes * 100, 1) if total_minutes else 0
                ),
                **library_stats,
            }
            self._mark_successful_update()

        except Exception as e:
            _log_api_error("Error fetching owned games from Steam", e)
            self._set_unavailable()

API_BADGES = "https://api.steampowered.com/IPlayerService/GetBadges/v1/"

class SteamProfileSensor(SteamBaseSensor):
    """Shows profile info like level and XP."""

    sensor_type = "profile"
    update_interval = timedelta(hours=6)
    def update(self):
        try:
            params = {"key": self._api_key, "steamid": self._steam_id}
            response = requests.get(API_BADGES, params=params, timeout=10)
            data = _response_data(response)
            profile_fields = (
                "player_level",
                "player_xp",
                "player_xp_needed_to_level_up",
                "player_xp_needed_current_level",
            )
            if any(
                type(data.get(field)) is not int or data[field] < 0
                for field in profile_fields
            ):
                raise ValueError("Steam profile level or XP data is unavailable")

            self._state = data["player_level"]
            self._attrs = {
                "player_xp": data.get("player_xp"),
                "player_xp_needed_to_level_up": data.get("player_xp_needed_to_level_up"),
                "player_xp_needed_current_level": data.get("player_xp_needed_current_level"),
            }
            self._mark_successful_update()
        except Exception as e:
            _log_api_error("Error fetching profile data from Steam", e)
            self._set_unavailable()

API_RECENT_GAMES = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"

class SteamRecentGamesSensor(SteamBaseSensor):
    """Shows recently played games."""

    sensor_type = "recent_games"
    update_interval = timedelta(minutes=10)
    
    def update(self):
        try:
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "count": 5,  # nur die letzten 5 Spiele
            }
            response = requests.get(API_RECENT_GAMES, params=params, timeout=10)
            data = _response_data(response)

            games = _response_list(data, "games", "total_count")
            if not games:
                self._state = "none"
                self._attrs = {"recent_games": [], "game_count": 0}
                self._mark_successful_update()
                return

            # Erstes Spiel als State
            first = games[0]
            self._state = first.get("name") or "unknown"

            # Spieleliste aufbereiten
            recent_games = [
                {
                    "appid": g.get("appid"),
                    "name": g.get("name"),
                    "playtime_2weeks_h": round(g.get("playtime_2weeks", 0) / 60, 1),
                    "playtime_total_h": round(g.get("playtime_forever", 0) / 60, 1),
                    "logo": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{g.get('appid')}/header.jpg",
                    "last_played": g.get("rtime_last_played")
                }
                for g in games
            ]

            self._attrs = {
                "recent_games": recent_games,
                "game_count": data.get("total_count", len(games)),
            }
            self._mark_successful_update()

        except Exception as e:
            _log_api_error("Error fetching recent games from Steam", e)
            self._set_unavailable()

API_ACHIEVEMENTS = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
API_SCHEMA = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
API_RECENT_GAMES = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"

class SteamRecentAchievementsSensor(SteamBaseSensor):
    """Shows achievement progress for recently played games."""

    sensor_type = "recent_achievements"
    update_interval = timedelta(hours=1)

    def update(self):
        try:
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "count": 5,  # only check the last 5 games
            }
            response = requests.get(API_RECENT_GAMES, params=params, timeout=15)
            games = _response_list(_response_data(response), "games", "total_count")
            _validate_achievement_games(games)

            achievements_data = []
            for g in games:
                appid = g.get("appid")
                name = g.get("name")

                unlocked, total = self._achievement_progress(appid, verify_schema=True)

                percent = None
                if total > 0:
                    percent = round((unlocked / total) * 100, 1)

                achievements_data.append({
                    "appid": appid,
                    "name": name,
                    "unlocked": unlocked,
                    "total": total,
                    "percent": percent,
                    "logo": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                })

            self._state = len(achievements_data)  # Anzahl Spiele mit Daten
            self._attrs = {"recent_achievements": achievements_data}
            self._mark_successful_update()

        except Exception as e:
            _log_api_error("Error fetching recent achievements", e)
            self._set_unavailable()


API_BADGES = "https://api.steampowered.com/IPlayerService/GetBadges/v1/"

class SteamGlobalStatsSensor(SteamBaseSensor):
    """Shows global achievement stats (expensive: iterates over all games)."""

    sensor_type = "global_stats"
    update_interval = timedelta(hours=24)
    
    def update(self):
        operation = "GetOwnedGames/v1"
        try:
            # 1) Alle Spiele abrufen
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "include_appinfo": True,
                "include_played_free_games": True,
            }
            resp = requests.get(API_OWNED_GAMES, params=params, timeout=30)
            games = _response_list(_response_data(resp), "games", "game_count")
            _validate_achievement_games(games)

            achievement_games = []
            for g in games:
                appid = g.get("appid")
                operation = "GetPlayerAchievements/v1"
                unlocked, total = self._achievement_progress(appid)
                achievement_games.append({
                    "appid": appid, "name": g.get("name"),
                    "unlocked": unlocked, "total": total,
                })
            achievement_stats = _global_achievement_statistics(achievement_games)

            # 3) Badges abrufen
            operation = "GetBadges/v1"
            badge_params = {"key": self._api_key, "steamid": self._steam_id}
            badge_resp = requests.get(API_BADGES, params=badge_params, timeout=10)
            badge_data = _response_data(badge_resp)
            badges = _response_list(badge_data, "badges")
            badge_count = len(badges)
            card_badge_count = len([b for b in badges if "appid" in b])

            # 4) Ergebnis
            self._state = achievement_stats["achievements_total"]
            self._attrs = {
                **achievement_stats,
                "badge_count": badge_count,
                "card_badge_count": card_badge_count,
            }
            self._mark_successful_update()

        except Exception as e:
            _log_api_error("Error fetching global stats", e, operation=operation)
            self._set_unavailable()

API_FRIENDS = "https://api.steampowered.com/ISteamUser/GetFriendList/v1/"
API_SUMMARIES = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

class SteamFriendsSensor(SteamBaseSensor):
    """Shows Steam friends and their current status."""

    sensor_type = "friends"
    update_interval = timedelta(minutes=5)

    def update(self):
        try:
            # step 1: get friends list
            params = {
                "key": self._api_key,
                "steamid": self._steam_id,
                "relationship": "friend"
            }
            resp = requests.get(API_FRIENDS, params=params, timeout=15)
            friends_data = _response_list(_response_data(resp, "friendslist"), "friends")

            if not friends_data:
                self._state = 0
                self._attrs = {"friends": []}
                self._mark_successful_update()
                return

            friend_ids = [f["steamid"] for f in friends_data]

            # step 2: get details for friends (max 100 per call)
            friends_info = []
            for i in range(0, len(friend_ids), 100):
                batch_ids = friend_ids[i:i+100]
                params = {"key": self._api_key, "steamids": ",".join(batch_ids)}
                info_resp = requests.get(API_SUMMARIES, params=params, timeout=15)
                players = _response_list(_response_data(info_resp), "players")
                if {player.get("steamid") for player in players} != set(batch_ids):
                    raise ValueError("Incomplete Steam friend summaries")
                for p in players:
                    state_map = {
                        0: "Offline",
                        1: "Online",
                        2: "Busy",
                        3: "Away",
                        4: "Snooze",
                        5: "Looking to trade",
                        6: "Looking to play",
                    }
                    persona_state = p.get("personastate")
                    status = (
                        state_map.get(persona_state, "Unknown")
                        if type(persona_state) is int else "Unknown"
                    )
                    friends_info.append({
                        "steamid": p.get("steamid"),
                        "personaname": p.get("personaname"),
                        "avatar": p.get("avatarfull"),
                        "profileurl": p.get("profileurl"),
                        "status": status,
                        "game": p.get("gameextrainfo"),
                    })

            self._state = len(friends_info)
            self._attrs = {"friends": friends_info}
            self._mark_successful_update()

        except Exception as e:
            _log_api_error("Error fetching friends list", e)
            self._set_unavailable()
