# Changelog

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
