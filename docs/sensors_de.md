# Steam Tracker: Sensorreferenz

[English](sensors_en.md) · [Installation und Einrichtung](../README.md) · [Companion Card](steam_tracker_card.md)

Diese Referenz beschreibt **Integration 0.9.8**. Version 0.9.8 ergänzt die sechs
zusätzlichen Global-Stats-Attribute weiter unten, die Schema-Gegenprüfung nach
einem Achievement-HTTP-500 und die strenge Prüfung einzelner Freundesstatus.
Version 0.9.5 enthält diese Ergänzungen nicht. Die Bibliothekskennzahlen stammen aus
0.7.1; `all_games.appid`, `all_games.playtime_minutes` und
`last_successful_update` wurden mit 0.9.5 ergänzt.

Die Integration funktioniert auch ohne Companion Card. Die Sensoren lassen sich
in eigenen Karten, Templates und Automationen verwenden. Alle Beispiele nutzen
erfundene Namen, Platzhalter-IDs und nicht erreichbare Bildadressen unter
`example.invalid`.

## Entitäten und Datentypen

Jedes über die Oberfläche eingerichtete Konto besitzt acht Sensoren unter einem
Kontogerät. Für ein neues Konto namens `Steam Tracker` sind dies die üblichen IDs:

| Entity-ID | `sensor_type` | Nativer Wert / Bedeutung | Intervall |
| --- | --- | --- | --- |
| `sensor.steam_tracker_status` | `status` | Status als Zeichenkette | 1 Minute |
| `sensor.steam_tracker_game` | `game` | Aktueller Spieltitel oder `none` | 2 Minuten |
| `sensor.steam_tracker_playtime` | `playtime` | Zahl, gesamte Lebenszeit-Spielstunden | 1 Stunde |
| `sensor.steam_tracker_profile` | `profile` | Ganzzahl, Steam-Level | 6 Stunden |
| `sensor.steam_tracker_recent` | `recent_games` | Erster zurückgegebener kürzlicher Spieltitel oder `none` | 10 Minuten |
| `sensor.steam_tracker_recent_achievements` | `recent_achievements` | Ganzzahl, Spiele mit lesbarem Erfolgsfortschritt | 1 Stunde |
| `sensor.steam_tracker_global_stats` | `global_stats` | Ganzzahl, insgesamt freigeschaltete Erfolge | 24 Stunden |
| `sensor.steam_tracker_friends` | `friends` | Ganzzahl, Anzahl der Freunde | 5 Minuten |

Bei einem neuen eigenen Kontonamen wie `Steam Account B` beginnen IDs normalerweise
mit `sensor.steam_account_b_steam_`. Registrierte IDs und selbst vergebene Namen
bleiben erhalten, auch nach dem Umbenennen des Dienstes. Die tatsächlichen IDs
stehen am Kontogerät. Unique-IDs verwenden `<steam_id>_<sensor_type>`; insbesondere
unterscheiden sich der Entity-Suffix `recent` und der Sensortyp `recent_games`.

Home Assistants `states()` liefert auch numerische Zustände als Zeichenketten.
Attribute behalten ihre JSON-Typen: Ganzzahl, Zahl, Zeichenkette, Liste, Objekt
oder `null`. Stundenwerte sind Stunden, Prozentwerte liegen zwischen 0 und 100.
Der aktuelle Code deklariert für diese Entitäten keine Home-Assistant-Metadaten
`unit_of_measurement`. Die Tabellen beschreiben die erwarteten Steam-Datentypen;
optionale Metadaten sind nicht garantiert und können `null` sein. Ein fehlendes
optionales Attribut ist kein bestätigter Nullwert.

## Leer, unbekannt und nicht verfügbar

| Wert | Bedeutung |
| --- | --- |
| `0` | Bestätigter Nullwert: beispielsweise leere Bibliothek, keine Freunde oder keine freigeschalteten Erfolge |
| `none` | Wörtlicher Sensorzustand: kein aktuelles beziehungsweise kein kürzlich gespieltes Spiel |
| `null` | JSON-Attributwert: unbekannte/fehlende Metadaten oder eine Quote ohne Nenner; in Jinja entspricht dies `none` |
| `Unknown` | Statusbezeichnung mit großem U; bei unbekanntem Statuscode sowie ab 0.9.8 bei fehlenden/ungültigen Freundesstatus |
| `unknown` | Home Assistants unbekannter Zustand; außerdem wörtlicher Ersatzwert, wenn dem ersten kürzlichen Spiel der Name fehlt |
| `unavailable` | Anfangszustand vor dem ersten erfolgreichen Abruf oder Fehler bei Hauptabfrage/erforderlichen Daten |

Nach einem fehlgeschlagenen Hauptabruf werden alter Zustand und sämtliche eigenen
Attribute einschließlich Erfolgszeitstempel verworfen. Der nächste gültige Abruf
stellt die Verfügbarkeit wieder her. Ein leeres Antwortobjekt bestätigt keine
leere Bibliothek. Fehlende Spielelisten zählen nur dann als leer, wenn Steam
ausdrücklich eine Ergebnisanzahl von null liefert. Für ergänzende Spielzeiten
des aktuellen Spiels und Top-5-Erfolge gelten die unten beschriebenen Ausnahmen.

Die Sichtbarkeit von Profil, Spieldetails und Freundesliste beeinflusst die
jeweiligen API-Daten. Private oder fehlende Daten können einzelne Sensoren
unverfügbar machen, während andere weiterarbeiten. Ein Timeout beweist weder
private Daten noch einen ungültigen Key. Nur HTTP 401/403 bei der Spielerübersicht
für Status/aktuelles Spiel startet bei UI-Konten eine erneute Authentifizierung.

## Gemeinsamer Zeitstempel und Aktualisierung

Jeder erfolgreiche Sensor enthält `last_successful_update` als ISO-8601-Zeitpunkt
in UTC, beispielsweise `2026-11-06T12:00:00+00:00`. Er bezeichnet einen erfolgreich
geprüften Abruf, auch bei unveränderten Werten und bestätigten leeren Ergebnissen.
Bei einem Hauptfehler wird er entfernt. Home Assistants `last_changed` und
`last_updated` sind kein Ersatz.

Status und aktuelles Spiel teilen je Konto einen 15 Sekunden gültigen Cache für
Spielerübersichten, auch bei YAML-Einrichtung. Gleichzeitige Leser teilen einen
Abruf. Nur erfolgreiche, lesbare Übersichten werden gespeichert. Ein Cache-Treffer
behält den ursprünglichen Abrufzeitpunkt. Andere Endpunkte und die ergänzende
Spielzeitabfrage nutzen diesen Cache nicht. Einrichtung und Key-Prüfungen fragen
Steam direkt ab; nach einem Neuladen des Kontos ist der Cache leer.

Jeder aktivierte Sensor wird beim Hinzufügen einmal und anschließend in seinem
Intervall aktualisiert. Langsame Global-Stats-Scans blockieren andere Sensoren
nicht. Ein laufender Abruf wird nicht nochmals gestartet. Entfernen/Entladen
beendet geplante Timer und die anfängliche Hintergrundaufgabe. Deaktiviertes
automatisches Polling in den Systemoptionen des Kontos stoppt die regelmäßigen
Timer, lässt den ersten Abruf aber zu. Die Intervalle sind fest; ein altes
YAML-`scan_interval` überschreibt sie nicht.

Eine manuelle Aktualisierung unter **Entwicklerwerkzeuge > Aktionen**:

```yaml
action: homeassistant.update_entity
target:
  entity_id: sensor.steam_tracker_global_stats
```

Die tatsächliche Entity-ID einsetzen. Ein laufender Scan beginnt nicht erneut;
Status/Spiel können eine weniger als 15 Sekunden alte Übersicht wiederverwenden.
**Zustand setzen** ändert nur die Darstellung in Home Assistant und ruft Steam
nicht ab. Nach einem Global-Stats-Fehler folgt sonst erst der nächste Tagesabruf;
eine frühere automatische Wiederholung ist noch nicht implementiert.

## Status

**Zustand:** Zeichenkette mit dem Spielerstatus. Fehlender oder nicht ganzzahliger
primärer `personastate` macht diesen Sensor unverfügbar. Ein unbekannter
ganzzahliger Code ergibt `Unknown`.

| Steam-Code | Zustand / Freundesstatus |
| --- | --- |
| 0 | `Offline` |
| 1 | `Online` |
| 2 | `Busy` |
| 3 | `Away` |
| 4 | `Snooze` |
| 5 | `Looking to trade` |
| 6 | `Looking to play` |
| Andere Ganzzahl | `Unknown` |

| Attribut | Typ | Bedeutung |
| --- | --- | --- |
| `personaname` | Zeichenkette oder null | Steam-Anzeigename |
| `profileurl` | Zeichenkette oder null | Profiladresse |
| `avatar` | Zeichenkette oder null | Adresse des großen Avatarbilds |
| `lastlogoff` | Ganzzahl oder null | Steams letzter Abmeldezeitpunkt als Unix-Sekunden seit UTC-Epoche; kein Zeitpunkt des letzten Integrationsabrufs |

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

## Aktuelles Spiel

**Zustand:** Spieltitel oder wörtlich `none`, wenn eine lesbare Übersicht kein
laufendes Spiel meldet. Nicht zugängliche Spieldaten bleiben unverfügbar. Ohne
laufendes Spiel enthält der Sensor nur den gemeinsamen Zeitstempel; die
spielspezifischen Attribute fehlen.

| Attribut | Typ | Bedeutung |
| --- | --- | --- |
| `gameid` | Zeichenkette | ID des laufenden Spiels, ausdrücklich als Text gespeichert |
| `name` | Zeichenkette | Aktueller Spieltitel |
| `personaname` | Zeichenkette oder null | Anzeigename des Spielers |
| `logo` | Zeichenkette | Aus der Spiel-ID abgeleitete Adresse des Kopfbilds |
| `total_playtime_hours` | Zahl, optional | Gesamte Spielzeit dieses Spiels in Stunden, eine Nachkommastelle |

Die Spielzeit ist ergänzend. Scheitert sie oder fehlt das Spiel in der
Bibliotheksantwort, entfällt `total_playtime_hours`; der Titel bleibt verfügbar.
Der Erfolgszeitstempel beschreibt weiterhin die Spielerübersicht und nicht die
ergänzende Anfrage.

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

## Spielzeit und Bibliotheksstatistik

**Zustand:** gesamte Lebenszeit-Spielstunden der zurückgegebenen Bibliothek,
eine Nachkommastelle. Eine ausdrücklich leere Bibliothek ergibt `0`. Fehlende,
negative, nicht ganzzahlige oder boolesche Lebenszeit-Minuten machen diesen
Sensor unverfügbar.

| Attribut | Typ | Bedeutung |
| --- | --- | --- |
| `game_count` | Ganzzahl | Anzahl zurückgegebener eigener Spiele |
| `total_playtime_hours` | Zahl | Derselbe Stundenwert wie der Zustand |
| `top_5_playtime_hours` | Zahl | Gesamte Stunden der fünf meistgespielten Spiele; gemeinsam aus Minuten berechnet und einmal gerundet |
| `top_5_games` | Liste | Bis zu fünf Spiele, absteigend nach exakten Lebenszeit-Minuten |
| `all_games` | Liste | Vollständige zurückgegebene Bibliothek, nach Namen sortiert |
| `playtime_by_gameid` | Objekt | App-ID als Zeichenkette → gerundete Lebenszeit-Stunden |
| `pile_of_shame_count` | Ganzzahl | Spiele unter 60 Minuten einschließlich ungespielter Spiele |
| `played_game_count` | Ganzzahl | Spiele mit mindestens einer aufgezeichneten Minute |
| `unplayed_game_count` | Ganzzahl | Spiele mit genau null aufgezeichneten Minuten |
| `unplayed_games` | Liste | Ungespielte Spiele nach Namen sortiert; je Ganzzahl `appid` und Zeichenkette/null `name` |
| `played_percentage` | Zahl | Gespielte / alle Spiele × 100, eine Nachkommastelle |
| `top_5_playtime_percentage` | Zahl | Exakte Top-5-Minuten / alle exakten Minuten × 100, eine Nachkommastelle |
| `playtime_distribution` | Objekt | Ganzzahlige Spieleanzahlen der fünf Gruppen unten |

Jeder Eintrag in `all_games` enthält `appid` (Ganzzahl), `name`
(Zeichenkette/null), `playtime_minutes` (exakte ganzzahlige Lebenszeit-Minuten)
und `hours` (Zahl mit einer Nachkommastelle). Version 0.9.5 ergänzt `appid` und
`playtime_minutes`; ältere Versionen können nur `name` und `hours` liefern.

Jeder Eintrag in `top_5_games` enthält `appid` (Ganzzahl), `name`
(Zeichenkette/null), `hours` (Zahl), `logo` (URL-Zeichenkette),
`achievements_unlocked` (Ganzzahl/null), `achievements_total` (Ganzzahl/null) und
`achievements_percent` (Zahl/null). Nicht lesbare ergänzende Erfolgsdaten setzen
alle drei Erfolgsfelder auf `null`, während die Spielzeit verfügbar bleibt.
Bestätigte Spiele ohne Erfolge haben 0/0 und Prozentwert `null`. Bestätigte
0/N mit N > 0 ergeben dagegen 0 Prozent.

| Schlüssel in `playtime_distribution` | Exakte Lebenszeit-Minuten |
| --- | --- |
| `unplayed` | 0 |
| `under_1_hour` | 1–59 |
| `1_to_10_hours` | 60–599 |
| `10_to_50_hours` | 600–2999 |
| `50_hours_or_more` | Ab 3000 |

Die Anzahlen ergeben zusammen `game_count`. Ein oder zwei Minuten zählen als
gespielt, auch wenn gerundete Stunden 0,0 anzeigen. Die Kennzahlen entstehen aus
derselben Bibliotheksantwort ohne zusätzliche Anfragen. Leere Bibliotheken
ergeben leere Listen/Objekte und null Anzahlen, Stunden und Prozentwerte. Bei
null Gesamtminuten ist der Top-5-Anteil 0 Prozent; es wird nicht durch null geteilt.

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

## Profil

**Zustand:** nicht negatives ganzzahliges Steam-Level einschließlich Level 0.
Alle drei XP-Felder müssen als nicht negative Ganzzahlen vorliegen; sonst ist
der Sensor unverfügbar.

| Attribut | Typ / Einheit | Bedeutung |
| --- | --- | --- |
| `player_xp` | Ganzzahl, XP | Insgesamt gesammelte XP |
| `player_xp_needed_to_level_up` | Ganzzahl, XP | Noch benötigte XP bis zum nächsten Level |
| `player_xp_needed_current_level` | Ganzzahl, XP | Gesamt-XP-Schwelle des aktuellen Levels, nicht noch fehlende XP |

Für einen Fortschrittsbalken ist `(player_xp - player_xp_needed_current_level)`
der erreichte Teil und `(player_xp + player_xp_needed_to_level_up -
player_xp_needed_current_level)` die gesamte Spanne. Eine nicht positive Spanne
ermöglicht keinen Prozentwert.

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

## Kürzlich gespielte Spiele

**Zustand:** Name des ersten Spiels in Steams Antwort oder `none` bei einem
ausdrücklich leeren Ergebnis. Angefragt werden bis zu fünf Spiele aus den letzten
zwei Wochen. Die Integration behält Steams Reihenfolge bei und sortiert nicht
nach `last_played`. Fehlt dem ersten Spiel der Name, lautet der Zustand `unknown`.

| Attribut | Typ | Bedeutung |
| --- | --- | --- |
| `game_count` | Ganzzahl | Steams `total_count`, möglicherweise größer als die fünf zurückgegebenen Einträge; fehlt das Feld, gilt die Listenlänge |
| `recent_games` | Liste | Bis zu fünf zurückgegebene Spiele |

| Feld in `recent_games` | Typ / Einheit | Bedeutung |
| --- | --- | --- |
| `appid` | Ganzzahl oder null | Steam-App-ID |
| `name` | Zeichenkette oder null | Spieltitel |
| `playtime_2weeks_h` | Zahl, Stunden | Spielzeit der letzten zwei Wochen, eine Nachkommastelle |
| `playtime_total_h` | Zahl, Stunden | Gesamte Lebenszeit-Spielstunden, eine Nachkommastelle |
| `logo` | Zeichenkette | Aus der App-ID abgeleitete Kopfbildadresse |
| `last_played` | Ganzzahl oder null | Unveränderte Unix-Sekunden aus `rtime_last_played`, falls geliefert; oft fehlend/null und in dieser Antwort nicht garantiert |

Dieser Parser ersetzt derzeit ausgelassene Spielzeit-Minutenfelder vor der
Umrechnung durch 0. Das unterscheidet sich von der strengen Minutenprüfung des
Bibliotheks-/Spielzeitsensors. Fehlende letzte Spielzeitpunkte werden nicht
gesondert nachgeladen.

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

## Kürzliche Erfolge

**Zustand:** Anzahl kürzlich gespielter Spiele mit bestätigten Erfolgsdaten,
höchstens fünf. Gemeint ist der **Gesamtfortschritt kürzlich gespielter Spiele**,
nicht die Anzahl oder Liste neu freigeschalteter Erfolge in einem Zeitraum. Ein
bestätigtes Spiel ohne Erfolge zählt ebenfalls als ein Spiel; eine leere Liste
kürzlicher Spiele ergibt Zustand 0.

Das Attribut `recent_achievements` enthält eine Liste dieser Felder:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `appid` | Ganzzahl | Steam-App-ID |
| `name` | Zeichenkette oder null | Spieltitel |
| `unlocked` | Ganzzahl | Freigeschaltete Erfolge |
| `total` | Ganzzahl | Mögliche Erfolge |
| `percent` | Zahl oder null | Freigeschaltet / gesamt × 100, eine Nachkommastelle; null bei Gesamtanzahl null |
| `logo` | Zeichenkette | Adresse des Spiel-Kopfbilds |

Jedes angefragte Spiel muss bestätigten Fortschritt liefern. Dieser Sensor
prüft außerdem die Erfolgskennungen gegen das Spielschema. Ein Fehler eines
Spiels macht den gesamten Sensor unverfügbar; es erscheint keine Teilliste.

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

**Zustand:** insgesamt freigeschaltete Erfolge in der zurückgegebenen eigenen
Bibliothek. Der Scan fragt Spielererfolge für jedes Spiel und anschließend die
Abzeichen ab. Sämtliche angefragten Fortschritts- und Abzeichendaten müssen
lesbar sein; Teilsummen werden nicht veröffentlicht. Daher kann der Fehler eines
einzelnen Spiels nur Global Stats unverfügbar machen.

| Attribut | Typ / Einheit | Bedeutung |
| --- | --- | --- |
| `achievements_total` | Ganzzahl | Insgesamt freigeschaltete Erfolge, identisch zum Zustand |
| `achievements_possible` | Ganzzahl | Insgesamt mögliche Erfolge |
| `perfect_games` | Ganzzahl | Spiele mit mindestens einem Erfolg, bei denen alle freigeschaltet sind |
| `avg_completion_rate` | Zahl, % | Arithmetischer Mittelwert der Spielabschlüsse, eine Nachkommastelle; jedes Spiel mit Erfolgen zählt gleich viel, einschließlich 0/N-Spielen |
| `badge_count` | Ganzzahl | Anzahl der von Steam zurückgegebenen Abzeicheneinträge |
| `card_badge_count` | Ganzzahl | Zurückgegebene Abzeichen mit `appid`: Spiel-/Sammelkartenabzeichen, nicht die Anzahl einzelner Sammelkarten |

### Zusätzliche Attribute — ab 0.9.8

Sie entstehen aus demselben vollständigen Scan **ohne weitere Steam-Abfragen**:

| Attribut | Typ | Bedeutung |
| --- | --- | --- |
| `achievements_remaining` | Ganzzahl | Mögliche minus freigeschaltete Erfolge |
| `overall_completion_rate` | Zahl oder null | Alle freigeschalteten / alle möglichen × 100, eine Nachkommastelle; null, wenn keine Erfolge möglich sind |
| `games_with_achievements` | Ganzzahl | Spiele mit Gesamtanzahl > 0 |
| `games_without_achievements` | Ganzzahl | Bestätigte Spiele ohne Erfolge |
| `completion_distribution` | Objekt | Ganzzahlige Anzahlen der sechs Abschlussgruppen unten |
| `completion_candidates` | Liste | Höchstens fünf unvollständige Spiele in der unten beschriebenen Reihenfolge |

Durchschnitt und Gesamtquote beantworten verschiedene Fragen: Spiele mit 1/1
und 0/99 ergeben durchschnittlich 50 Prozent Abschluss, insgesamt aber 1 Prozent
Erfolgsquote. Spiele ohne Erfolge zählen bei beiden Quoten und perfekten Spielen
nicht mit. Eine leere Bibliothek beziehungsweise eine Bibliothek ohne Erfolge
ergibt null Anzahlen, eine leere Kandidatenliste, `avg_completion_rate: 0` und
`overall_completion_rate: null`.

| Schlüssel in `completion_distribution` | Exakter Fortschritt |
| --- | --- |
| `not_started` | 0 % |
| `under_25` | Größer als 0 %, kleiner als 25 % |
| `25_to_50` | Mindestens 25 %, kleiner als 50 % |
| `50_to_75` | Mindestens 50 %, kleiner als 75 % |
| `75_to_100` | Mindestens 75 %, kleiner als 100 % |
| `complete` | 100 % |

Die Gruppen verwenden exakte Anzahlen vor jeder Rundung. Ihre Summe entspricht
`games_with_achievements`; `complete` entspricht `perfect_games`. Spiele ohne
Erfolge stehen separat. Kandidaten enthalten `appid` als Ganzzahl, `name` als
Zeichenkette/null, `unlocked`, `total` und `remaining` als Ganzzahlen sowie
`percent` als Zahl mit einer Nachkommastelle. Es gilt 0 ≤ unlocked < total.
Sortiert wird nach wenigsten verbleibenden Erfolgen, höchster exakter Quote,
Namen ohne Beachtung der Großschreibung und schließlich App-ID. Unbegonnene
Spiele können Kandidaten sein; vollständige Spiele und Spiele ohne Erfolge
nicht. Auf 100 Prozent gerundeter Fortschritt macht ein unvollständiges Spiel
nicht zu einem perfekten Spiel.

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

### Verfügbarkeit und Fehlerdiagnose bei Erfolgen

Spielerfortschritte benötigen eindeutige gültige Erfolgskennungen und ganzzahlige
`achieved`-Werte 0 oder 1. Eine mehrdeutige Antwort „Requested app has no stats“
oder eine fehlende/leere Erfolgsliste erfordert ein gültiges Schema, das keine
Erfolge bestätigt. Ein erfolgreiches `{"game": {}}` oder ein gültiges Spielobjekt
ohne Erfolgsdefinitionen bestätigt dies. Fehlende/ungültige Schemaobjekte und
fehlgeschlagene Schema-Abfragen bestätigen keine leere Liste.

**Ab 0.9.8:** Ein Achievement-HTTP-500 startet ebenfalls diese
Schema-Gegenprüfung. Der Scan geht nur weiter, wenn das Schema keine Erfolge
bestätigt. Enthält es Erfolge, bleibt der ursprüngliche HTTP-Fehler beim
Spielerfortschritt erhalten. Fehlgeschlagene/ungültige Schemata bleiben Fehler.
Andere HTTP- und Transportfehler werden nicht zu null Erfolgen. Global Stats und
Top-5 benötigen normalerweise eine Spielerabfrage pro Spiel; Schemata kommen bei
mehrdeutigen Antworten oder HTTP 500 hinzu. Kürzliche Erfolge prüfen das Schema
immer.

**Ab 0.9.8:** Global Stats protokolliert die Operation
(`GetOwnedGames/v1`, `GetPlayerAchievements/v1`, `GetSchemaForGame/v2` oder
`GetBadges/v1`), bei Erfolgs-/Schemafehlern die numerische `appid`, den
Ausnahmetyp und gegebenenfalls den HTTP-Status. API-Keys, Konto-IDs,
Request-URLs, Antwortinhalte und beliebige Ausnahmetexte werden nicht ausgegeben.
Validierungsfehler können weiterhin nur als `ValueError` erscheinen; daraus ist
nicht jedes fehlerhafte Antwortfeld erkennbar.

## Freunde

**Zustand:** Anzahl zurückgegebener Freunde. Eine ausdrücklich leere Liste
ergibt 0 und `friends: []`. Freundesübersichten werden in Gruppen von höchstens
100 IDs geladen. Fehlt ein Freund in den Übersichten oder scheitert eine
Anfrage, wird der Sensor unverfügbar.

Das Attribut `friends` ist eine Liste dieser Felder:

| Feld | Typ | Bedeutung |
| --- | --- | --- |
| `steamid` | Zeichenkette | SteamID64 des Freundes; Beispiele verwenden Platzhalter |
| `personaname` | Zeichenkette oder null | Anzeigename |
| `avatar` | Zeichenkette oder null | Adresse des großen Avatarbilds |
| `profileurl` | Zeichenkette oder null | Steam-Profiladresse |
| `status` | Zeichenkette | Bezeichnungen aus der Status-Tabelle |
| `game` | Zeichenkette oder null | Aktueller Spieltitel, sofern von Steam geliefert |

**Ab 0.9.8:** Nur der ganzzahlige Statuscode 0 bedeutet
`Offline`. Fehlende, nicht ganzzahlige (einschließlich boolescher und
Fließkommawerte) und unbekannte Codes ergeben für diesen Freund `Unknown`.
Ein lesbarer Freund bleibt in Liste und Anzahl; andere Freunde werden dadurch
nicht unverfügbar. Codes 0–6 behalten ihre Bedeutung. Eine fehlende oder
fehlgeschlagene Freundesübersicht bleibt ein Hauptfehler. Die Companion Card
übersetzt `Unknown` und berücksichtigt den Status nicht im Online-Filter.

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

Vor dem Lesen eines Zustands in Automationen `has_value('sensor.deine_entity')`
prüfen. Optionale Attribute ausdrücklich auf `none` prüfen; pauschales `or 0`
macht aus unbekannten Daten einen erfundenen Nullwert. Sensorzustände und
Attributschlüssel behalten ihre technische Sprache; die Karte kann
Anzeigetexte übersetzen.
