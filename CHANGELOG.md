# Changelog

## 0.9.0 - 2026-11-04

### Changes

- Update the companion-card documentation and fictional previews for Steam
  Tracker Card 0.8.0: independent title/account-label visibility, offline
  last-online time, online current-game details, view icons, separated game
  rows, and revised library-statistics presentation.
- Document all eight card views, the three layouts, and current compatibility
  using release versions.
- Bump the integration release to 0.9.0. Sensor behavior, attributes, update
  intervals, configuration, and API request counts are unchanged from 0.7.1.

### Updating from 0.7.1

- Update the integration and restart Home Assistant. No sensor or dashboard
  migration is required.
- Update Steam Tracker Card separately to 0.8.0 and reload the browser. For a
  manual card installation use `/local/steam-tracker-card.js?v=0.8.0` to refresh
  the cache. Card UI improvements are supplied by that separate frontend asset.
- Minimum supported Home Assistant version remains 2025.10.0.

### Validation

- Python syntax, integration/HACS JSON validation, and Git whitespace checks.
- 18 regression tests on Python 3.13 with Home Assistant Core 2025.10.0 and
  mocked Steam HTTP, including achievement scans, library minute boundaries,
  recovery, request counts, and DE/EN template rendering.
- Companion card: JavaScript syntax, 14 logic tests, and browser checks for
  the updated UI, both languages, all layouts, account isolation, and mobile.
- No authenticated Steam requests were made. Live Home Assistant frontend
  behavior and HACS installation remain to be verified.

## 0.7.1 - 2026-11-03

### Changes

- Accept successful empty achievement schemas for games without statistics,
  preventing those games from making Global Stats or Recent Achievements
  unavailable or leaving top-five achievement fields unknown.
- Extend the playtime sensor with played and unplayed game counts, a sorted
  unplayed-games list, played percentage, top-five playtime percentage, and
  five mutually exclusive playtime groups.
- Calculate library metrics from the exact lifetime minutes already fetched;
  short sessions remain played even when rounded hours display zero. Missing
  or invalid minutes make the sensor unavailable instead of inventing zeroes.
- Update the German and English library card/dashboard examples, attribute
  documentation, and companion-card preview. No additional Steam API calls,
  sensor renaming, or unique-ID changes are introduced.

### Updating from 0.7.0

- Update the integration and restart Home Assistant. The initial sensor refresh
  provides the new attributes without waiting for the next scheduled update.
- Update Steam Tracker Card separately to 0.7.2 for the new library tiles and
  distribution bars, then reload the browser. The YAML examples can also be
  used independently. Existing card configurations remain valid.
- Minimum supported Home Assistant version remains 2025.10.0.

### Validation

- Python syntax, integration/HACS JSON, and Git whitespace checks.
- 18 regression tests with Home Assistant Core 2025.10.0 and mocked Steam HTTP:
  achievement schemas, library aggregation, exact minute boundaries, empty and
  invalid data, recovery, request counts, and DE/EN YAML template rendering.
- Companion card: JavaScript syntax, 13 logic tests, and browser checks for the
  new statistics, older sensors, empty data, all layouts, languages, and mobile.
- No authenticated Steam requests were made. Live Home Assistant frontend
  behavior and HACS installation remain to be verified.

## 0.7.0 - 2026-11-03

### Changes

- Name newly created account sensors after their service, for example
  `sensor.yourusername_steam_friends`. UI entities use the account device name as
  their prefix. The default `Steam Tracker` naming remains unchanged.
- Preserve registered entity IDs, unique IDs, and user-assigned names when
  updating or renaming a service.
- Include a local integration icon in normal and high resolution, with SVG
  source, for Home Assistant 2026.3 and newer.
- Update the companion card documentation and previews for its eight views,
  smaller compact layout, single-line layout, library search, and friend filters.
  The separately installed Steam Tracker Card is released as 0.7.0 as well.

### Updating from 0.6.0

- Update through HACS and restart Home Assistant. Existing dashboard and
  automation references keep working; existing entity IDs are not rewritten.
- To adopt the new naming for existing entities, rename their IDs in Home
  Assistant and update the corresponding dashboard and automation references.
- Update the companion card separately and reload the browser. Manual card
  installations should use `steam-tracker-card.js?v=0.7.0` to refresh the cache.
- Minimum supported Home Assistant version remains 2025.10.0. Local icon display
  requires Home Assistant 2026.3 or newer.

### Validation

- Python syntax and integration/HACS JSON validation.
- Isolated Home Assistant Core 2025.10 checks with mocked Steam responses:
  configuration flow, all eight sensors, custom and default names, two accounts,
  service rename, preservation of registered IDs and custom names, reload/unload,
  and legacy YAML naming. No authenticated Steam requests were made.
- Local icon dimensions, PNG format, and transparency checked.
- Actual icon rendering in a Home Assistant frontend and HACS installation
  remain to be verified in a live instance.

## 0.6.0 - 2026-11-03

### Changes

- Group each UI-configured Steam account and its eight sensors under a separate
  service device. Existing sensor unique IDs and entity IDs are preserved.
- Schedule independent sensor updates and reduce the frequency of expensive
  global achievement scans to once per day. Slow library scans can run alongside
  status updates, and timers are removed when entities are disabled or unloaded.
- Report unavailable or invalid Steam data as `unavailable`, clear stale values,
  and recover after a successful refresh. Explicitly empty results remain valid.
- Validate achievement responses and distinguish unknown progress from games
  confirmed to have no achievements. Incomplete achievement scans no longer
  publish partial totals.
- Avoid including Steam request URLs or credentials in API error logs.
- Update the German and English example cards and dashboards to handle
  unavailable data and unknown achievement progress.
- Document the optional, separately installed Steam Tracker Card and update
  repository links.

### Updating from 0.5.2

- Install the release through HACS and restart Home Assistant.
- No sensor renaming is required. Existing dashboard and automation entity
  references are preserved.
- Automations should handle `unavailable` states explicitly. Unknown achievement
  values can be `null`, and games without achievements have no completion
  percentage.
- Update intervals are fixed per sensor; legacy YAML `scan_interval` settings no
  longer override them. See the README for the interval table.
- Minimum supported Home Assistant version remains 2025.10.0.

### Validation

- Python syntax and integration/HACS JSON validation.
- Home Assistant runtime and HACS installation have not been verified in a test
  instance for this release.
