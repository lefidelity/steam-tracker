# Steam Tracker Card

[Steam Tracker Card](https://github.com/lefidelity/steam-tracker-card) displays the
integration's sensors in a Home Assistant dashboard. It is optional and installed
separately from the integration. Both projects have source version **1.0.0**.

[English](#english) · [Deutsch](#deutsch) · [All views and layouts](steam_tracker_card_visual_guide.md)

![Eight card views in Steam blue, English, with fictional data](images/steam_tracker_card_preview.png)

## English

### Views and installation

The card provides eight views: `profile`, `current_game`, `recent_games`,
`library_stats`, `player_stats`, `top_games`, `friends`, and `games`.
Choose detailed, compact, or single-line layouts, German/English labels,
Home Assistant theme colors, or Steam blue. Friends and the full library include
search; the library also has sorting and playtime filters.

Use the card's [installation and configuration guide](https://github.com/lefidelity/steam-tracker-card#installation)
for HACS or manual installation. The card needs no Steam key and makes no Steam
API requests. Game images and avatars normally load from Steam's image servers
in the browser. No additional custom cards are required.

The visual editor selects the account and view. Registered sensors are discovered
by their integration and unique IDs, so renamed entity IDs continue to work.
Manual assignment supports legacy YAML sensors and users without registry access.

### Statistics

Library statistics show played and unplayed counts, played percentage, top-five
playtime share, and five playtime groups. One recorded minute counts as played.
The under-one-hour tile includes unplayed games; the under-one-hour distribution
bar counts only games with 1–59 minutes.

Player statistics show achievement counts, average progress per game, the overall
unlocked percentage, six completion groups, badges, and up to five games closest
to 100%. Average progress weights each game equally; the overall percentage
counts all unlocked achievements against all possible achievements.

![Player statistics with fictional data](images/steam_tracker_achievement_statistics.png)

The optional `show_data_status: true` footer shows the oldest successful fetch
time among the displayed sensors. Its source is `last_successful_update`, not
Home Assistant's state-change timestamp.

![Data freshness with fictional player statistics](images/steam_tracker_card_data_status.png)

For older installations: library statistics require integration 0.7.1, exact-minute
filters and data freshness require 0.9.5, and the additional achievement statistics
require 0.9.8. Integration 1.0.0 provides all of these attributes. The
[English sensor reference](sensors_en.md) documents the complete data format.

### One view

With a single discovered account:

```yaml
type: custom:steam-tracker-card
view: player_stats
layout: detailed
language: en
```

### Two accounts

Choose each account in its card's visual editor. Replace these placeholder IDs
with the values saved by the editor; they are not Steam IDs or display names.

```yaml
type: vertical-stack
cards:
  - type: custom:steam-tracker-card
    view: profile
    account: ACCOUNT_DEVICE_ID_A
    language: en
  - type: custom:steam-tracker-card
    view: profile
    account: ACCOUNT_DEVICE_ID_B
    language: en
```

### Manual sensor assignment

Use the actual entity IDs from Home Assistant and keep all assignments on the
intended account. A card configuration must not contain an API key.

```yaml
type: custom:steam-tracker-card
view: player_stats
layout: compact
language: en
entities:
  global_stats: sensor.steam_tracker_global_stats
```

## Deutsch

### Ansichten und Installation

Die Karte bietet acht Ansichten: `profile`, `current_game`, `recent_games`,
`library_stats`, `player_stats`, `top_games`, `friends` und `games`.
Zur Wahl stehen Ausführlich, Kompakt und Einzeiler, deutsche/englische Texte
sowie Home-Assistant-Theme oder Steam-Blau. Freunde und die gesamte Bibliothek
besitzen eine Suche; die Bibliothek zusätzlich Sortierung und Spielzeitfilter.

Die [Installations- und Konfigurationsanleitung](https://github.com/lefidelity/steam-tracker-card/blob/main/docs/README_de.md#installation)
beschreibt HACS und die manuelle Installation. Die Karte benötigt keinen
Steam-Key und fragt die Steam-API nicht ab. Bilder und Avatare lädt der Browser
normalerweise von Steams Bildservern. Zusätzliche Custom Cards sind nicht nötig.

Konto und Ansicht werden im visuellen Editor gewählt. Registrierte Sensoren
werden über Integration und Unique-IDs erkannt; umbenannte Entity-IDs funktionieren
weiter. Manuelle Zuweisungen unterstützen YAML-Sensoren und Benutzer ohne
Registrierungszugriff.

### Statistiken

Die Bibliothek-Statistik zeigt gespielte und ungespielte Spiele, den Anteil
gespielter Spiele, den Top-5-Spielzeitanteil und fünf Spielzeitgruppen. Eine
erfasste Minute zählt als gespielt. Die Kachel unter einer Stunde schließt
ungespielte Spiele ein; der Verteilungsbalken zählt nur Spiele mit 1–59 Minuten.

Die Spieler-Statistik zeigt Erfolgsanzahlen, den durchschnittlichen Fortschritt
pro Spiel, die Gesamtquote freigeschalteter Erfolge, sechs Abschlussgruppen,
Abzeichen und bis zu fünf Spiele **Am nächsten dran an 100%**. Beim Durchschnitt
zählt jedes Spiel gleich; die Gesamtquote teilt alle freigeschalteten durch alle
möglichen Erfolge.

![Library statistics with fictional data](images/steam_tracker_library_statistics.png)

Mit `show_data_status: true` zeigt die Karte den ältesten erfolgreichen Abruf
der angezeigten Sensoren. Grundlage ist `last_successful_update`, nicht der
Zeitpunkt einer Zustandsänderung in Home Assistant.

Für ältere Installationen: Die Bibliothekskennzahlen benötigen Integration 0.7.1,
Minutenfilter und Datenstand 0.9.5, die zusätzlichen Erfolgsstatistiken 0.9.8.
Integration 1.0.0 liefert alle genannten Attribute. Die
[deutsche Sensorreferenz](sensors_de.md) beschreibt das vollständige Datenformat.

### Eine Ansicht

Bei einem einzelnen erkannten Konto:

```yaml
type: custom:steam-tracker-card
view: player_stats
layout: detailed
language: de
```

### Zwei Konten

Jedes Konto im visuellen Editor seiner Karte wählen. Die Platzhalter durch die
vom Editor gespeicherten IDs ersetzen; es sind keine Steam-IDs oder Anzeigenamen.

```yaml
type: vertical-stack
cards:
  - type: custom:steam-tracker-card
    view: profile
    account: ACCOUNT_DEVICE_ID_A
    language: de
  - type: custom:steam-tracker-card
    view: profile
    account: ACCOUNT_DEVICE_ID_B
    language: de
```

### Sensor manuell zuweisen

Die tatsächlichen Entity-IDs verwenden und alle Zuordnungen auf das gewünschte
Konto beschränken. Ein API-Key gehört nicht in die Kartenkonfiguration.

```yaml
type: custom:steam-tracker-card
view: player_stats
layout: compact
language: de
entities:
  global_stats: sensor.steam_tracker_global_stats
```
