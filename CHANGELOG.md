# Changelog

## 0.9.9 - 2026-11-08

### Changes

- Add the full MIT license and copyright notice to the repository and the
  installable integration directory so component-only ZIPs include the license.
- Link the license from the README.

### Distribution

- Bump the integration source version to 0.9.9 alongside Steam Tracker Card 0.9.9.
  Commit and push the source changes without publishing GitHub releases or assets.
- Sensor behavior, attribute contracts, and minimum card compatibility remain
  unchanged from integration 0.9.8.

### Validation

- Python syntax, integration/HACS JSON, matching MIT license copies, and Git
  whitespace checks passed. Integration Python code and tests are unchanged.
- Companion card: JavaScript syntax, 21 logic tests, and browser checks passed.
  No authenticated Steam requests were made.

## 0.9.8 - 2026-11-06

### Changes

- Replace complete dashboard and third-party custom-card examples with central
  English/German sensor references covering every sensor, state, nested field,
  unit, calculation, availability rule, and fictional response example. Keep
  small companion-card configurations for one view, accounts, and manual IDs.
- Remove the retired dashboard screenshot and both template-only test modules.
  Preserve sensor/API/config-flow/cache regression tests and keep the main README
  focused on installation, setup, sensor overview, and documentation links.
- Report missing, invalid, and unrecognized friend presence as `Unknown`; only
  integer presence code 0 means `Offline`. Keep valid codes 0–6 unchanged and
  retain readable friends in the list without adding requests. Failed or
  incomplete summary requests still invalidate the friends sensor.
- Add the overall achievement rate, remaining achievement count, exact completion
  distribution, and up to five completion candidates to Global Stats using the
  existing complete scan, with no additional Steam requests. Keep existing
  fields, sensor IDs, states, and equal-weight average completion unchanged.
- Count games without achievements separately. Exclude them and completed games
  from candidates; preserve unknown progress as unavailable. Document attributes,
  ranking, empty results, and companion-card compatibility in both languages.
- Identify the failed API operation in global-stats error logs and include the
  numeric app ID for achievement/schema failures. Preserve exception types and
  HTTP status without logging request URLs, keys, account IDs, or untrusted text.
- Check the game schema after an achievement HTTP 500. Continue only when a
  successful, valid schema confirms no achievements; never skip unreadable
  progress for a game with achievements. Apply the same rule to global stats,
  recent achievements, and supplementary top-game achievement data.
- Keep full-scan availability checks, successful-request counts, and update
  intervals intact. A player-achievement HTTP 500 adds one schema request.
- Document manual refresh and add mocked failure/recovery and log-privacy checks.

### Updating

- Update the integration to 0.9.8 and restart Home Assistant. Existing account
  entries, entity IDs, sensor states, and supported attributes remain compatible.
- Update Steam Tracker Card separately to 0.9.8 and reload the browser. Manual
  installations can use `/local/steam-tracker-card.js?v=0.9.8` for cache refresh.
- The additional player-statistics tiles, completion groups, and candidates
  require integration 0.9.8 and card 0.9.8 together. Older sensors keep their
  supported card display without fabricated replacement data.
- Full dashboard and third-party card examples have been retired. Use the
  English/German sensor references or the small companion-card configurations.
- Friends with missing or invalid presence now show `Unknown` instead of a
  fabricated offline status. No sensor or attribute key migration is needed.

### Validation

- 60 retained tests passed on Python 3.13 with Home Assistant Core 2025.10.0 and
  mocked Steam HTTP, including exact completion groups, candidate ranking,
  unchanged request counts, HTTP-500 schema confirmation,
  failure/recovery, privacy, unchanged handling of other HTTP errors, and friend
  presence validation (missing/invalid values, all valid codes, and recovery).
- Remove seven template-rendering checks with the retired examples. Validate
  the 16 matching JSON examples and all 46 sensor/list fields across both new
  references, nine retained YAML blocks, and 95 local documentation links/anchors.
- Companion card: JavaScript syntax, 21 logic tests, and Playwright checks passed
  for both languages, three layouts, old/invalid/empty data, safe name actions,
  mobile sizing, and existing views. Preview images use fictional data.
- Python syntax, integration/HACS JSON, and Git whitespace checks passed.
- No authenticated Steam requests were made by the checks. The user confirmed
  the schema fallback on Home Assistant; new statistics still require live
  installation verification of both updated projects.

## 0.9.5 - 2026-11-05

### Changes

- Check new accounts and explicit imports against Steam using a 17-digit
  SteamID64 and a password field. Distinguish access denied, connection/timeouts,
  missing accounts, and unreadable responses. Private libraries do not block setup.
- Add native API-key reconfiguration and reauthentication. Validate replacement
  keys before saving, reload the same account entry, and preserve device/entity
  IDs, names, options, and other accounts. Duplicate accounts cannot replace keys.
- Request reauthentication only for HTTP 401/403 from the status/current-game
  player-summary endpoint. Keep timeouts and private game/achievement failures
  separate, and keep credentials and untrusted exception text out of errors/logs.
- Add `appid` and exact lifetime `playtime_minutes` to `all_games`, preserving
  rounded `hours`, existing states/attributes, and the owned-games request budget.
  These fields support Steam Tracker Card 0.9.5 library filters and Steam links.
- Add `last_successful_update` to all eight sensors. Record real successful
  fetches, including unchanged values and confirmed empty results. Failed updates
  clear stale data; incomplete global achievement scans never publish success.
- Share status/current-game player summaries in a 15-second cache per account,
  including legacy YAML setups. Concurrent readers share one request. Failed or
  incomplete results are not cached, and expired data is never used after errors.
  Account reloads/key changes start empty; credential-validation flows stay uncached.
- Preserve the original summary fetch time on cache hits. Other endpoints and
  supplementary current-game playtime remain outside the cache. Sensor intervals
  and the Home Assistant minimum version (2025.10.0) are unchanged.
- Update English/German configuration text, documentation, fictional previews,
  library labels, and the optional data-freshness example.

### Updating

- Update the integration to 0.9.5 and restart Home Assistant. Existing account
  entries, sensor IDs, dashboards, and automations remain usable.
- Update Steam Tracker Card separately to 0.9.5 and reload the browser. Manual
  card installations can use `/local/steam-tracker-card.js?v=0.9.5` for cache refresh.
- Library range filters, full-library Steam links, and the data-freshness footer
  require integration 0.9.5 data. Older sensors retain their supported card features.
- Change a key through the account entry's **Reconfigure** menu. A failed check
  leaves the old key unchanged. Legacy YAML still reads its key from YAML/secrets;
  it does not automatically initiate UI import.
- Manual status/current-game refreshes can reuse summaries younger than 15 seconds;
  a cache hit keeps its original data-freshness time.

### Validation

- 50 integration/template/API/config-flow/cache tests passed on Python 3.13 with
  Home Assistant Core 2025.10.0 and mocked Steam HTTP, including parallel readers,
  exact cache expiry, account/key isolation, reload wiring, failures, and recovery.
- Python syntax, integration/HACS JSON, documentation links, and Git whitespace checks.
- Companion card: JavaScript syntax, 18 logic tests, and browser checks for both
  languages, all views/layouts, filters/actions, editor, mobile, safe rendering,
  successful-fetch timestamps, and timer/subscription cleanup.
- No authenticated Steam requests were made. Live Home Assistant frontend behavior
  and HACS installation compatibility remain to be tested.

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
