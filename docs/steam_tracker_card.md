# Steam Tracker Card companion

[**Steam Tracker Card**](https://github.com/lefidelity/steam-tracker-card) is a
separate frontend project named `steam-tracker-card`.
It provides profile, current game, recently played, library statistics, player
statistics, top-five games, friends, and full-library views. Detailed, compact,
and single-line layouts are available. Friends and the full library include
search and filtering or sorting. A visual editor selects the account, view, layout, appearance,
language, and display options. Multiple cards can be combined into a dashboard.
The editor can independently hide the upper-right account label and the title,
preserving any custom title. Offline profiles show a relative last-online time
below their status in detailed and compact layouts when `lastlogoff` is available.
Online players with a current game see “Playing: <game name>” there instead,
using the same account's existing current-game sensor without extra Steam requests.

![All eight Steam Tracker Cards in Steam blue, full layout, English, with fictional demo data](images/steam_tracker_card_preview.png)

[Visual guide: all card views and variants](steam_tracker_card_visual_guide.md).
Compare [Steam blue / English](steam_tracker_card_visual_guide/steam-en.md),
[Home Assistant theme / English](steam_tracker_card_visual_guide/theme-en.md),
[Steam blue / German](steam_tracker_card_visual_guide/steam-de.md), and
[Home Assistant theme / German](steam_tracker_card_visual_guide/theme-de.md).
Every view has Full, Compact, and Single line images. The Home Assistant theme
uses a light reference theme; the card inherits your own theme colors at runtime.

The card reads the existing sensors and attributes. It does not make Steam API
requests, need a Steam API key, or require button-card, bar-card, or card-mod.
Library statistics now include played percentage, unplayed games, top-five
playtime share, and a five-group playtime distribution when the updated
integration provides those attributes. Older sensor data keeps the original
statistics; detailed and compact layouts show the distribution bars.
The card uses view-specific heading icons, separators and top-aligned artwork
for recent/top-five games, and the revised library tile order and distribution labels.

![Library statistics with fictional demo data](images/steam_tracker_library_statistics.png)

It identifies registered sensors using the `steam_tracker` platform and their
existing unique IDs. Account devices are available from integration 0.6.0;
older registered entities can be grouped by config entry. Manual
assignments support legacy YAML sensors and users without registry access.

The local project is at `../steam-tracker-card` relative to this repository and
contains English/German installation instructions, `dist/steam-tracker-card.js`,
an interactive preview, and automated logic/browser checks. The GitHub repository
is [lefidelity/steam-tracker-card](https://github.com/lefidelity/steam-tracker-card).
HACS validation and tests in a real Home Assistant instance are still pending.
The integration is released as 0.9.0 and the card as 0.8.0; install and update
them separately. Library additions require integration 0.7.1 or newer;
profile details use existing status and current-game attributes.

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
Kontoname rechts oben und Titel lassen sich getrennt ausblenden; ein eigener
Titel bleibt gespeichert. Offline-Profile zeigen in Ausführlich und Kompakt die
letzte Onlinezeit unter dem Status, sofern `lastlogoff` verfügbar ist.
Bei online verbundenen Spielern mit laufendem Spiel steht dort stattdessen
„Spielt: <Spielname>“, aus dem vorhandenen Spielsensor desselben Kontos.

Die [Bild-Dokumentation](steam_tracker_card_visual_guide.md) zeigt alle acht
Ansichten in Steam-Blau und Home-Assistant-Theme, Deutsch und Englisch sowie
Voll, Kompakt und Einzeilig: insgesamt 96 Einzelbilder. Direkt zu den deutschen
Vergleichen für [Steam-Blau](steam_tracker_card_visual_guide/steam-de.md) und
[Home-Assistant-Theme](steam_tracker_card_visual_guide/theme-de.md).
Die Gesamtübersicht darüber zeigt Steam-Blau, Voll und Englisch.

Die Bibliothek-Statistik ergänzt Spielquote, ungespielte Spiele, Top-5-Anteil und
eine Spielzeit-Verteilung in fünf Gruppen, sobald die aktualisierte Integration
die Attribute liefert. Ausführlich und Kompakt zeigen die Verteilung als Balken;
ältere Sensordaten behalten die bisherige Darstellung. Die Karte nutzt passende
Titelsymbole, Trennlinien und oben bündige Bilder für kürzlich gespielte und
Top-5-Spiele sowie die neue Kachelreihenfolge und Verteilungsbeschriftung.

Das lokale Git-Projekt liegt neben dieser Integration im Ordner
`steam-tracker-card`. Vorschau, deutsche Anleitung und Prüfungen sind dort
enthalten. Das GitHub-Repository ist
[lefidelity/steam-tracker-card](https://github.com/lefidelity/steam-tracker-card).
Die [deutsche Installationsanleitung](https://github.com/lefidelity/steam-tracker-card/blob/main/docs/README_de.md#installation)
beschreibt HACS und die manuelle Installation. HACS-Validierung und Tests in einer
echten Home-Assistant-Instanz stehen noch aus.

Für beide Projekte wird kein `hacs-`-Präfix benötigt. Das Integrationsrepository
heißt auf GitHub `lefidelity/steam-tracker`; Dokumentation, Manifest, HACS-Link
und lokales Git-Remote verwenden diesen Namen. Die Integration erscheint als
Version 0.9.0, die Karte als 0.8.0; beide werden separat installiert.
Die technische Domain bleibt
`steam_tracker`; eine Änderung der Sensor-IDs ist für den Repository-Namen nicht nötig.
