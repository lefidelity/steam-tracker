Open Home Assistant, go to your dashboard, click the three dots → **Edit dashboard** → three dots again → **Raw configuration editor**, and paste the contents of the desired YAML file. The easiest way to copy everything is to open the file on GitHub and use the **Raw** view.

For multiple Steam accounts, copy the dashboard for each account and replace all
`sensor.steam_tracker_*` references with the actual entity IDs listed under that
account in Steam Tracker. For a new account named `Steam Account B`, these will
normally start with `sensor.steam_account_b_`. Existing entity IDs are preserved.

Bei mehreren Steam-Konten kannst du das Dashboard für jedes Konto kopieren.
Ersetze alle Verweise auf `sensor.steam_tracker_*` durch die tatsächlichen
Entity-IDs des jeweiligen Kontos. Bei einem neu eingerichteten Konto namens
`Steam Account B` beginnen sie normalerweise mit `sensor.steam_account_b_`.
Bereits bestehende Entity-IDs bleiben erhalten.

The example makes use of a few popular custom cards. Install them via HACS so the layout renders correctly:

- [button-card](https://github.com/custom-cards/button-card)
- [config-template-card](https://github.com/iantrich/config-template-card)
- [entity-progress-card](https://github.com/t1m0thyj/entity-progress-card)
- [bar-card](https://github.com/custom-cards/bar-card)
- [flex-table-card](https://github.com/custom-cards/flex-table-card)
- [card-mod](https://github.com/thomasloven/lovelace-card-mod)

![Sample Steam dashboard built with the example configuration.](docs/examples/dashboard_example.jpg)

Feel free to adapt the cards, colors, or layout to match your own setup.
