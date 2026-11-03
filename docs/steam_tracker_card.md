# Steam Tracker Card companion

[**Steam Tracker Card**](https://github.com/lefidelity/steam-tracker-card) is a
separate frontend project named `steam-tracker-card`.
It provides profile, current game, recently played, library statistics, player
statistics, top-five games, friends, and full-library views. Detailed, compact,
and single-line layouts are available. Friends and the full library include
search and filtering or sorting. A visual editor selects the account, view, layout, appearance,
language, and display options. Multiple cards can be combined into a dashboard.

![Steam Tracker Card with fictional demo accounts and games](images/steam_tracker_card_preview.png)

Layout previews: [Compact](images/steam_tracker_card_compact.png) ·
[Single line](images/steam_tracker_card_single_line.png).

The card reads the existing sensors and attributes. It does not make Steam API
requests, need a Steam API key, or require button-card, bar-card, or card-mod.
It identifies registered sensors using the `steam_tracker` platform and their
existing unique IDs. Account devices are available from integration commit
`89b2fb8`; older registered entities can be grouped by config entry. Manual
assignments support legacy YAML sensors and users without registry access.

The local project is at `../steam-tracker-card` relative to this repository and
contains English/German installation instructions, `dist/steam-tracker-card.js`,
an interactive preview, and automated logic/browser checks. The GitHub repository
is [lefidelity/steam-tracker-card](https://github.com/lefidelity/steam-tracker-card).
HACS validation and tests in a real Home Assistant instance are still pending.
Both projects publish version 0.7.0 and are installed separately.

See the card's [installation instructions](https://github.com/lefidelity/steam-tracker-card#installation)
for HACS custom repository and manual installation steps.

## Repository names

Use **Steam Tracker** / `steam-tracker` for the integration and
**Steam Tracker Card** / `steam-tracker-card` for the card. A `hacs-` prefix is not
needed; HACS is a distribution method. The card has an independent
Git repository with its own version.

The integration repository is [lefidelity/steam-tracker](https://github.com/lefidelity/steam-tracker).
Documentation, manifest links,
the HACS installation link, and the local Git remote use the new repository name.
The integration domain remains `steam_tracker`; the repository name does not
require changing sensor IDs or attributes.

## Deutsche Kurzfassung

Die separate **Steam Tracker Card** bietet Profil, aktuelles Spiel, kürzlich
gespielte Spiele, Bibliothek-Statistik, Spieler-Statistik, Top-5-Spiele, Freunde
und die Spiele-Gesamtübersicht. Die Darstellungen Ausführlich, Kompakt und
Einzeiler sind verfügbar; Freunde und Spiele besitzen Suche und Filter
beziehungsweise Sortierung. Im visuellen Editor lassen sich Konto und Ansicht
sowie Darstellung, Sprache und weitere Optionen auswählen. Die Karte liest
vorhandene Sensoren und benötigt weder einen API-Key noch weitere Custom Cards.

Das lokale Git-Projekt liegt neben dieser Integration im Ordner
`steam-tracker-card`. Vorschau, deutsche Anleitung und Prüfungen sind dort
enthalten. Das GitHub-Repository ist
[lefidelity/steam-tracker-card](https://github.com/lefidelity/steam-tracker-card).
Die [deutsche Installationsanleitung](https://github.com/lefidelity/steam-tracker-card/blob/main/docs/README_de.md#installation)
beschreibt HACS und die manuelle Installation. HACS-Validierung und Tests in einer
echten Home-Assistant-Instanz stehen noch aus.

Für beide Projekte wird kein `hacs-`-Präfix benötigt. Das Integrationsrepository
heißt auf GitHub `lefidelity/steam-tracker`; Dokumentation, Manifest, HACS-Link
und lokales Git-Remote verwenden diesen Namen. Beide Projekte veröffentlichen
Version 0.7.0 und werden separat installiert. Die technische Domain bleibt
`steam_tracker`; eine Änderung der Sensor-IDs ist für den Repository-Namen nicht nötig.
