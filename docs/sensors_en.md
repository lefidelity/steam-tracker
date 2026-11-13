# Steam Tracker sensor reference

[Deutsch](sensors_de.md) · [Installation and setup](../README.md) · [Companion card](steam_tracker_card.md)

This reference describes **integration 1.0.0**: all eight sensors, their states,
attributes, calculations, and failure handling. Earlier versions may lack newer
attributes; compatibility notes identify them where relevant.

The integration works without the companion card. Use its sensors in your own
cards, templates, or automations. All examples below use fictional names,
placeholder identifiers, and nonfunctional `example.invalid` image URLs.

## Entities and data types

Each UI-configured account has eight sensors under one account device. These
are the usual IDs for a new account named `Steam Tracker`:

| Entity ID | `sensor_type` | Native value / meaning | Interval |
| --- | --- | --- | --- |
| `sensor.steam_tracker_status` | `status` | Presence string | 1 minute |
| `sensor.steam_tracker_game` | `game` | Current game title or `none` | 2 minutes |
| `sensor.steam_tracker_playtime` | `playtime` | Number, total lifetime hours | 1 hour |
| `sensor.steam_tracker_profile` | `profile` | Integer, Steam level | 6 hours |
| `sensor.steam_tracker_recent` | `recent_games` | First returned recent game title or `none` | 10 minutes |
| `sensor.steam_tracker_recent_achievements` | `recent_achievements` | Integer, number of games with readable progress | 1 hour |
| `sensor.steam_tracker_global_stats` | `global_stats` | Integer, total unlocked achievements | 24 hours |
| `sensor.steam_tracker_friends` | `friends` | Integer, number of friends | 5 minutes |

For a new custom account named `Steam Account B`, IDs normally start with
`sensor.steam_account_b_steam_`. Existing registered IDs and user-assigned names
are preserved, including after service renaming; look up the actual IDs on the
account device. Unique IDs use `<steam_id>_<sensor_type>`. In particular, the
`recent` entity ID and `recent_games` sensor type are different.

Home Assistant's `states()` returns strings even for numeric sensor values.
Attributes retain their JSON types: integer, number, string, list, object, or
`null`. Hours are measured in hours and percentages in 0–100; the current code
does not declare a Home Assistant `unit_of_measurement` for these entities.
Tables describe expected Steam data types; optional metadata is not guaranteed
and can be `null`. A missing optional attribute is different from a zero value.

## Empty, unknown, and unavailable values

| Value | Meaning |
| --- | --- |
| `0` | A confirmed zero, such as an empty library, zero friends, or no unlocked achievements |
| `none` | Literal state string: no current game, or no recent games |
| `null` | JSON attribute value: unknown/absent metadata or a percentage without a denominator; Jinja reads it as `none` |
| `Unknown` | Presence label for an unrecognized code or missing/invalid friend presence |
| `unknown` | Home Assistant's unknown state; the recent-games parser also uses this literal if the first returned game lacks a name |
| `unavailable` | Initial state before the first successful refresh, or a failed primary request/invalid required data |

A failed primary refresh clears the previous state and all custom attributes,
including the success timestamp. The next valid refresh restores availability.
An empty response object does not prove an empty library. Missing games lists
count as empty only when Steam explicitly reports a zero result count.
Supplementary current-game playtime and top-five achievement failures follow
the more permissive rules documented below.

Public profile, game details, and friends-list visibility affect the corresponding
API data. Private or missing data can make individual sensors unavailable while
other sensors continue working. A timeout alone does not prove privacy or an
invalid key. Only HTTP 401/403 from the status/current-game player-summary request
starts reauthentication for accounts configured through the UI.

## Shared timestamp and refresh behavior

After a successful refresh, each sensor includes `last_successful_update`, an ISO 8601 UTC string,
for example `2026-11-06T12:00:00+00:00`. It records a successful validated fetch,
including unchanged values and confirmed empty results. It is cleared on primary
failure. Home Assistant's `last_changed` and `last_updated` are not substitutes.

Status and current game share a 15-second in-memory player-summary cache per
account, including legacy YAML setups. Simultaneous readers share one fetch.
Only successful, readable summaries are cached; a cache hit keeps the original
fetch timestamp. Other endpoints and supplementary game playtime are outside
this cache. Setup/key-validation requests bypass it. Account reloads start empty.

Each enabled sensor refreshes once on addition, then at its own interval in the
table above. Slow Global Stats scans do not block the other sensors. An update
already running is not started again. Removal/unload cancels scheduled timers
and the initial background task. Disabling automatic polling in the config
entry's system options stops periodic timers but still allows the initial fetch.
Intervals are fixed; legacy YAML `scan_interval` does not override them.

To request a refresh under **Developer tools > Actions**:

```yaml
action: homeassistant.update_entity
target:
  entity_id: sensor.steam_tracker_global_stats
```

Use your actual entity ID. An existing scan is not restarted; status/game can
reuse a summary younger than 15 seconds. **Set state** only changes Home
Assistant's representation and does not contact Steam. Failed Global Stats
refreshes otherwise wait for the next daily interval; no shorter automatic
retry is implemented.

## Status

**State:** presence string. Missing or noninteger primary `personastate` makes
this sensor unavailable; an unrecognized integer yields `Unknown`.

| Steam code | State / friend presence |
| --- | --- |
| 0 | `Offline` |
| 1 | `Online` |
| 2 | `Busy` |
| 3 | `Away` |
| 4 | `Snooze` |
| 5 | `Looking to trade` |
| 6 | `Looking to play` |
| Other integer | `Unknown` |

These are the sensor values used by automations. Steam Tracker Card displays
`Snooze` as **Idle** in English and **Inaktiv** in German; it does not rename the
sensor value.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `personaname` | string or null | Steam display name |
| `profileurl` | string or null | Profile URL |
| `avatar` | string or null | Full-size avatar URL |
| `lastlogoff` | integer or null | Steam's last-logoff Unix timestamp, seconds since UTC epoch; not the last successful integration refresh |

```json
{
  "state": "Online",
  "attributes": {
    "personaname": "Player One",
    "profileurl": "https://steamcommunity.com/id/fictional-player-one/",
    "avatar": "https://example.invalid/avatar.png",
    "lastlogoff": 1793966400,
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Current game

**State:** game title, or literal `none` when a readable summary contains no
current-game information and has valid presence data. An explicitly non-public
summary without game information is unavailable. With `none`, only the shared
timestamp is present; game-specific attributes are absent. A missing game field
alone does not tell the integration whether game activity is hidden.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `gameid` | string | Current game ID, deliberately stored as text |
| `name` | string | Current game title |
| `personaname` | string or null | Player display name |
| `logo` | string | Game header-image URL derived from the game ID |
| `total_playtime_hours` | number, optional | Lifetime playtime for this game, rounded to one decimal |

Playtime is supplementary. Its failure or a missing owned-games match omits
`total_playtime_hours` without invalidating the game title. The success timestamp
continues to describe the player-summary fetch, not the supplementary request.

```json
{
  "state": "Beyond the Blue",
  "attributes": {
    "gameid": "101",
    "name": "Beyond the Blue",
    "personaname": "Player One",
    "logo": "https://example.invalid/game-101.jpg",
    "total_playtime_hours": 1.5,
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Playtime and library statistics

**State:** total lifetime hours across the returned owned-games library, rounded
to one decimal. An explicitly empty library is `0`. Missing, negative,
noninteger, or boolean lifetime minutes invalidate this sensor.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `game_count` | integer | Number of returned owned games |
| `total_playtime_hours` | number | Same hours value as the state |
| `top_5_playtime_hours` | number | Combined lifetime hours of the five most-played games, rounded once from their summed minutes |
| `top_5_games` | list | Up to five games, descending by exact lifetime minutes |
| `all_games` | list | Full returned library, sorted by name |
| `playtime_by_gameid` | object | String app ID → rounded lifetime hours |
| `pile_of_shame_count` | integer | Games below 60 minutes, including unplayed games |
| `played_game_count` | integer | Games with at least one recorded minute |
| `unplayed_game_count` | integer | Games with exactly zero recorded minutes |
| `unplayed_games` | list | Unplayed games sorted by name, each with integer `appid` and string/null `name` |
| `played_percentage` | number | Played games / all games × 100, one decimal |
| `top_5_playtime_percentage` | number | Top-five raw minutes / all raw minutes × 100, one decimal |
| `playtime_distribution` | object | Integer game counts in the five groups below |

Each `all_games` item has `appid` (integer), `name` (string/null),
`playtime_minutes` (exact integer lifetime minutes), and `hours` (number, one
decimal). Version 0.9.5 adds `appid` and `playtime_minutes`; older versions can
have only `name` and `hours`.

Each `top_5_games` item has `appid` (integer), `name` (string/null), `hours`
(number), `logo` (URL string), `achievements_unlocked` (integer/null),
`achievements_total` (integer/null), and `achievements_percent` (number/null).
Unreadable supplementary achievements make all three achievement fields `null`
while playtime stays available. Confirmed games without achievements have counts
0/0 and percentage `null`. A genuine 0/N with N > 0 has percentage 0.

| `playtime_distribution` key | Exact lifetime minutes |
| --- | --- |
| `unplayed` | 0 |
| `under_1_hour` | 1–59 |
| `1_to_10_hours` | 60–599 |
| `10_to_50_hours` | 600–2999 |
| `50_hours_or_more` | 3000 or more |

These counts sum to `game_count`. One or two minutes still count as played even
when displayed hours round to 0.0. The usage metrics use the owned-games response
already fetched, with no additional requests. Empty libraries have empty lists
and maps and zero counts, hours, and percentages. Zero total minutes gives a
top-five share of 0%, not a division error.

```json
{
  "state": "1.5",
  "attributes": {
    "game_count": 2,
    "total_playtime_hours": 1.5,
    "top_5_playtime_hours": 1.5,
    "all_games": [
      {"appid": 101, "name": "Beyond the Blue", "playtime_minutes": 90, "hours": 1.5},
      {"appid": 102, "name": "Paper Harbor", "playtime_minutes": 0, "hours": 0.0}
    ],
    "top_5_games": [
      {"appid": 101, "name": "Beyond the Blue", "hours": 1.5, "logo": "https://example.invalid/game-101.jpg", "achievements_unlocked": 1, "achievements_total": 2, "achievements_percent": 50.0},
      {"appid": 102, "name": "Paper Harbor", "hours": 0.0, "logo": "https://example.invalid/game-102.jpg", "achievements_unlocked": 0, "achievements_total": 0, "achievements_percent": null}
    ],
    "playtime_by_gameid": {"101": 1.5, "102": 0.0},
    "pile_of_shame_count": 1,
    "played_game_count": 1,
    "unplayed_game_count": 1,
    "unplayed_games": [{"appid": 102, "name": "Paper Harbor"}],
    "played_percentage": 50.0,
    "top_5_playtime_percentage": 100.0,
    "playtime_distribution": {"unplayed": 1, "under_1_hour": 0, "1_to_10_hours": 1, "10_to_50_hours": 0, "50_hours_or_more": 0},
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Profile

**State:** nonnegative integer Steam level, including level 0. All three XP
fields must be present as nonnegative integers or the sensor is unavailable.

| Attribute | Type / unit | Meaning |
| --- | --- | --- |
| `player_xp` | integer, XP | Total accumulated XP |
| `player_xp_needed_to_level_up` | integer, XP | XP still required to reach the next level |
| `player_xp_needed_current_level` | integer, XP | Total-XP threshold for the current level, not XP still missing |

For a level-progress bar, use `(player_xp - player_xp_needed_current_level)` as
progress and `(player_xp + player_xp_needed_to_level_up -
player_xp_needed_current_level)` as the span. A zero/nonpositive span cannot
produce a percentage.

```json
{
  "state": "3",
  "attributes": {
    "player_xp": 450,
    "player_xp_needed_to_level_up": 150,
    "player_xp_needed_current_level": 300,
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Recent games

**State:** the first game's name in Steam's response, or `none` for an explicitly
empty result. The integration requests up to five games from the last two weeks
and preserves Steam's order; it does not sort by `last_played`. A missing first
name falls back to the literal state `unknown`.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `game_count` | integer | Steam's `total_count`, which may exceed the returned five entries; falls back to list length when omitted |
| `recent_games` | list | Up to five returned game records |

| Field in `recent_games` | Type / unit | Meaning |
| --- | --- | --- |
| `appid` | integer or null | Steam app ID |
| `name` | string or null | Game title |
| `playtime_2weeks_h` | number, hours | Last-two-weeks playtime, one decimal |
| `playtime_total_h` | number, hours | Lifetime playtime, one decimal |
| `logo` | string | Header-image URL derived from app ID |
| `last_played` | integer or null | Raw `rtime_last_played` Unix seconds if supplied; often absent/null and not guaranteed by this response |

This parser currently defaults omitted playtime minute fields to 0 before
converting to hours. This differs from the strict owned-library minute validation
in the playtime sensor. It does not fetch missing last-played timestamps.

```json
{
  "state": "Beyond the Blue",
  "attributes": {
    "game_count": 1,
    "recent_games": [{"appid": 101, "name": "Beyond the Blue", "playtime_2weeks_h": 1.0, "playtime_total_h": 1.5, "logo": "https://example.invalid/game-101.jpg", "last_played": null}],
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Recent achievements

**State:** number of recently played games with confirmed achievement data, up
to five. This is **overall progress for recent games**, not the number or a feed
of newly unlocked achievements in a time window. A confirmed game without
achievements still contributes one game; an empty recent list gives state 0.

`recent_achievements` is a list with these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `appid` | integer | Steam app ID |
| `name` | string or null | Game title |
| `unlocked` | integer | Unlocked achievements |
| `total` | integer | Possible achievements |
| `percent` | number or null | Unlocked / total × 100, one decimal; null when total is zero |
| `logo` | string | Game header-image URL |

Every requested game must have confirmed progress. This sensor also checks the
player achievement identifiers against the game schema. A per-game failure
invalidates the whole sensor, rather than returning a partial list.

```json
{
  "state": "2",
  "attributes": {
    "recent_achievements": [
      {"appid": 101, "name": "Beyond the Blue", "unlocked": 1, "total": 2, "percent": 50.0, "logo": "https://example.invalid/game-101.jpg"},
      {"appid": 102, "name": "Paper Harbor", "unlocked": 0, "total": 0, "percent": null, "logo": "https://example.invalid/game-102.jpg"}
    ],
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

## Global Stats

**State:** total unlocked achievements across the returned owned library. The
scan requests player achievements for every owned game and badges afterwards.
All requested progress and badge data must be readable; no partial totals are
published. A single game's error can make Global Stats unavailable even while
other sensors work.

| Attribute | Type / unit | Meaning |
| --- | --- | --- |
| `achievements_total` | integer | Total unlocked achievements, same as the state |
| `achievements_possible` | integer | Total possible achievements |
| `perfect_games` | integer | Games with at least one achievement and all of them unlocked |
| `avg_completion_rate` | number, % | Arithmetic mean of per-game completion percentages, one decimal; each game with achievements has equal weight, including 0/N games |
| `badge_count` | integer | Number of badge records returned by Steam |
| `card_badge_count` | integer | Number of returned badges with an `appid`: game/trading-card badges, not the number of individual trading cards |

### Completion breakdown (available since 0.9.8)

These use the same complete scan, with **no additional Steam requests**:

| Attribute | Type | Meaning |
| --- | --- | --- |
| `achievements_remaining` | integer | Possible minus unlocked achievements |
| `overall_completion_rate` | number or null | All unlocked / all possible × 100, one decimal; null if no achievements are possible |
| `games_with_achievements` | integer | Games with total > 0 |
| `games_without_achievements` | integer | Games confirmed to have no achievements |
| `completion_distribution` | object | Integer counts in the six groups below |
| `completion_candidates` | list | Up to five incomplete games ranked as described below |

Average completion and the overall percentage weight the data differently: games at
1/1 and 0/99 have an average completion of 50% and an overall rate of 1%.
Games without achievements are excluded from both rates and perfect-game counts.
An empty/no-achievement library gives zero counts, an empty candidate list,
`avg_completion_rate: 0`, and `overall_completion_rate: null`.

| `completion_distribution` key | Exact completion |
| --- | --- |
| `not_started` | 0% |
| `under_25` | Greater than 0%, less than 25% |
| `25_to_50` | At least 25%, less than 50% |
| `50_to_75` | At least 50%, less than 75% |
| `75_to_100` | At least 75%, less than 100% |
| `complete` | 100% |

Groups use exact counts before rounding and sum to `games_with_achievements`.
`complete` equals `perfect_games`; games without achievements are separate.
Candidate items contain integer `appid`, string/null `name`, integer `unlocked`,
`total`, and `remaining`, plus number `percent` rounded to one decimal. Only games
with 0 ≤ unlocked < total qualify. Sort order is fewest remaining achievements,
highest exact completion ratio, case-insensitive name, then app ID. Unstarted
games can qualify; completed games and games without achievements cannot. A
display percentage rounded to 100% does not make an incomplete game perfect.

```json
{
  "state": "1",
  "attributes": {
    "achievements_total": 1,
    "achievements_possible": 2,
    "perfect_games": 0,
    "avg_completion_rate": 50.0,
    "badge_count": 2,
    "card_badge_count": 1,
    "achievements_remaining": 1,
    "overall_completion_rate": 50.0,
    "games_with_achievements": 1,
    "games_without_achievements": 1,
    "completion_distribution": {"not_started": 0, "under_25": 0, "25_to_50": 0, "50_to_75": 1, "75_to_100": 0, "complete": 0},
    "completion_candidates": [{"appid": 101, "name": "Beyond the Blue", "unlocked": 1, "total": 2, "remaining": 1, "percent": 50.0}],
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

### Achievement availability and diagnosis

Player progress must contain distinct valid achievement identifiers and integer
`achieved` values 0 or 1. An ambiguous "Requested app has no stats" reply or a
missing/empty achievement list requires a valid schema confirming no achievements.
A successful `{"game": {}}`, or a valid game object without achievement definitions,
confirms none. Missing/invalid schema objects and failed schema requests do not.

**From 0.9.8:** an achievement HTTP 500 also triggers that schema check.
The scan continues only if the schema confirms no achievements. When the schema
contains achievements, the original player-progress HTTP failure is retained;
failed/invalid schemas remain failures. Other HTTP errors and transport failures
are not converted to zero. Normal Global Stats/top-five progress uses one player
request per game, with schema requests for ambiguous results or HTTP 500; Recent
Achievements always verifies the schema.

**From 0.9.8:** Global Stats logs the operation (`GetOwnedGames/v1`,
`GetPlayerAchievements/v1`, `GetSchemaForGame/v2`, or `GetBadges/v1`), numeric
`appid` for achievement/schema failures, exception type, and HTTP status when
available. It does not print API keys, account IDs, request URLs, response bodies,
or arbitrary exception messages. Validation errors can still appear as generic
`ValueError`; this does not identify every invalid response field.

## Friends

**State:** number of returned friends. An explicitly empty list gives 0 and
`friends: []`. Friend summaries are requested in batches of up to 100 IDs.
Missing friends in the summaries or failed requests make the sensor unavailable.

`friends` is a list with these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `steamid` | string | Friend's SteamID64; examples use placeholders |
| `personaname` | string or null | Display name |
| `avatar` | string or null | Full-size avatar URL |
| `profileurl` | string or null | Steam profile URL |
| `status` | string | Presence labels from the Status table |
| `game` | string or null | Current game title if Steam supplies it |

**From 0.9.8:** only integer presence code 0 means `Offline`.
Missing, noninteger (including boolean and floating-point), and unrecognized
codes yield `Unknown` for that friend. A readable friend remains in the count
and list; this does not invalidate other friends. Existing codes 0–6 retain their
meaning. A missing/failed friend summary remains a primary failure. The companion
card translates `Unknown` and excludes it from its online-only filter.

```json
{
  "state": "2",
  "attributes": {
    "friends": [
      {"steamid": "FRIEND_A_PLACEHOLDER", "personaname": "Alex", "avatar": "https://example.invalid/alex.png", "profileurl": "https://steamcommunity.com/id/fictional-alex/", "status": "Online", "game": "Beyond the Blue"},
      {"steamid": "FRIEND_B_PLACEHOLDER", "personaname": "Jamie", "avatar": null, "profileurl": null, "status": "Unknown", "game": null}
    ],
    "last_successful_update": "2026-11-06T12:00:00+00:00"
  }
}
```

For automations, use `has_value('sensor.your_entity')` before reading a state.
For optional attributes, test for `none` explicitly; a blanket `or 0` converts
unknown data into a fabricated zero. Sensor states and attribute keys stay in
their technical language; display labels can be localized by the card.
