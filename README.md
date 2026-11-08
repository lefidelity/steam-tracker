# Steam Tracker for Home Assistant

Steam Tracker exposes Steam account data as eight Home Assistant sensors:
player presence, current game, playtime, level and XP, recent games, achievement
progress, library-wide statistics, and friends.

- [Sensor reference (English)](docs/sensors_en.md)
- [Sensorreferenz (Deutsch)](docs/sensors_de.md)
- [Steam Tracker Card and small configuration examples](docs/steam_tracker_card.md)
- [Visual guide to the companion card](docs/steam_tracker_card_visual_guide.md)

The integration works independently of the optional companion card. It is not
affiliated with Valve or Steam.

## Installation

Home Assistant **2025.10.0 or newer** is required, as declared in `hacs.json`.
The integration and companion card have independent repositories and versions;
install and update each separately. The current source version is **0.9.9** for
both projects. No GitHub release is published for this version.

### HACS

1. Open HACS and look for **Steam Tracker** under integrations.
2. If it is not listed, open **Custom repositories**, add
   `https://github.com/lefidelity/steam-tracker` as an **Integration**, and search again.
3. Download the integration and restart Home Assistant.

[![Open Steam Tracker in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lefidelity&repository=steam-tracker&category=integration)

### Manual installation

Copy the release's `custom_components/steam_tracker` directory into
`<your Home Assistant configuration>/custom_components/steam_tracker`, then
restart Home Assistant.

The integration includes local brand images for Home Assistant 2026.3 and newer.
Older supported versions can run the integration without those local images.

## Steam account preparation

You need a **17-digit SteamID64** and a **Steam Web API key**. Find the SteamID64
under your Steam account details, and obtain a key from
[Steam's API-key page](https://steamcommunity.com/dev/apikey). For the registration
form, a domain such as `localhost` can be used. Keep the key private.

Illustrations: [find the SteamID64](docs/images/retrieve_steam_id.png) and
[register an API key](docs/images/create_web_api_key.png).

Steam visibility settings determine which data can be read:

| Setting in Edit profile > Privacy settings | Data affected |
| --- | --- |
| My Profile | Profile information and presence |
| Game Details | Library, playtime, current/recent games, and achievement progress |
| Friends List | Friends and their available presence data |

Make the relevant sections public for the data you want to expose. Private or
inaccessible data can leave individual sensors `unavailable`; it is not treated
as an empty library or as zero achievements. A timeout alone does not mean the
key is invalid or the profile is private. See the
[sensor availability rules](docs/sensors_en.md#empty-unknown-and-unavailable-values).

## Configuration

1. Open **Settings > Devices & Services > Add integration**.
2. Select **Steam Tracker**.
3. Enter the SteamID64, API key, and account name.

From integration 0.9.5, setup validates the input and makes one player-summary
request before saving. It distinguishes access denied, connection/timeouts,
missing accounts, and unreadable responses. A private games library does not
prevent account setup. Duplicate Steam accounts are rejected without changing
existing keys. API-key input uses a password field.

### Multiple accounts and entity IDs

Add another account with **Add service** on the Steam Tracker integration page.
Each UI-configured account has a separate service entry and account device with
eight sensors; accounts can be reloaded or removed independently.

With the default name `Steam Tracker`, entity IDs normally start with
`sensor.steam_tracker_`. A new custom name such as `Steam Account B` normally
produces `sensor.steam_account_b_steam_*`. Existing registered IDs and custom
names remain unchanged, including after service renaming. Check the actual IDs
on the account device before using manual assignments or automations.

The companion card can discover accounts and sensors through its visual editor;
its automatic assignment does not require the default account name.

### Change an API key

Open the affected account entry's menu and select **Reconfigure**. Steam must
confirm the replacement key for the same account before it is saved. A failed
check leaves the old key unchanged. A successful change reloads that account
while preserving entity IDs, names, options, and other accounts.

HTTP 401/403 from status/current-game player summaries starts reauthentication
for UI accounts. Timeouts and inaccessible game/achievement data do not.

### Legacy YAML

Legacy YAML remains supported and reads the API key from YAML or its secret;
it does not automatically migrate to a UI entry. Account devices and key-change
menus require UI configuration.

```yaml
sensor:
  - platform: steam_tracker
    api_key: !secret steam_api_key
    steam_id: "STEAM_ID64_PLACEHOLDER"
    name: "Steam Tracker"
```

Replace the placeholder with your own SteamID64. Keep real credentials and
account data out of repository files and public issue reports.

## Sensors

| Default entity ID | Value |
| --- | --- |
| `sensor.steam_tracker_status` | Presence, such as `Online` or `Offline` |
| `sensor.steam_tracker_game` | Current game title or `none` |
| `sensor.steam_tracker_playtime` | Total lifetime hours |
| `sensor.steam_tracker_profile` | Steam level |
| `sensor.steam_tracker_recent` | First returned recent game title or `none` |
| `sensor.steam_tracker_recent_achievements` | Number of recent games with confirmed achievement progress |
| `sensor.steam_tracker_global_stats` | Total unlocked achievements |
| `sensor.steam_tracker_friends` | Number of friends |

The [English sensor reference](docs/sensors_en.md) and
[deutsche Sensorreferenz](docs/sensors_de.md) document all states, attribute and
list-item types, units, refresh intervals, privacy/failure behavior, calculations,
and fictional examples. They identify the Global Stats additions and
friend-presence/schema fixes introduced in 0.9.8 alongside earlier features.

Every successful sensor includes `last_successful_update` from integration
0.9.5. Fixed update intervals range from one minute to one day. Manual refresh,
the short shared player-summary cache, and `0` / `none` / `null` / `Unknown` /
`unknown` / `unavailable` are explained in the references.

## Dashboard card

[Steam Tracker Card](https://github.com/lefidelity/steam-tracker-card) is the
recommended optional dashboard frontend. It provides eight views, a visual
editor, account selection, German/English labels, and detailed, compact, or
single-line layouts. It reads these sensors without a Steam key, Steam requests,
or additional custom-card dependencies.

See the [card overview and small examples](docs/steam_tracker_card.md) for one
view, multiple accounts, and manual sensor assignment. The
[visual guide](docs/steam_tracker_card_visual_guide.md) compares all views and
layouts. The former complete dashboards and examples for third-party custom
cards have been removed; sensor data remains available for your own dashboards.
Live Home Assistant frontend and HACS installation checks are separate from the
synthetic preview/browser tests.

## Contributing and verification

Issues and pull requests are welcome. Include reproduction steps, Home Assistant
and integration/card versions, expected behavior, and relevant sanitized logs.
Never include API keys, request URLs containing credentials, or real account data.

With a compatible Home Assistant/Python environment and dependencies including
`requests`, run the mocked integration tests:

```text
python -m unittest discover -s tests -v
```

The tested baseline is Home Assistant Core 2025.10.0 on Python 3.13. These tests
mock Steam HTTP; they do not make authenticated Steam requests. Sensor, API,
config-flow, cache, and statistics regression tests remain. Template-rendering
tests tied to the removed dashboards/examples have been removed with them.
The companion card has its own logic/browser checks in its repository.

See [CHANGELOG.md](CHANGELOG.md) for release changes and executed checks.

## License

Steam Tracker is distributed under the [MIT License](LICENSE).
The full license and copyright notice are also included in
`custom_components/steam_tracker/LICENSE` so they accompany the integration
when installed or distributed as `steam_tracker.zip`.
