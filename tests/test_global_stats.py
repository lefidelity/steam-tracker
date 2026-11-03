"""Regression checks for library-wide achievement scans with mocked Steam HTTP."""

import json
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.sensor import (
    API_ACHIEVEMENTS,
    API_BADGES,
    API_OWNED_GAMES,
    API_RECENT_GAMES,
    API_SCHEMA,
    SteamGlobalStatsSensor,
    SteamPlaytimeSensor,
    SteamRecentAchievementsSensor,
)


def response(payload, status=200):
    """Create an HTTP response without sending a request."""
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode()
    return result


class GlobalStatsTests(unittest.TestCase):
    """Exercise the complete update, including availability and recovery."""

    def setUp(self):
        self.sensor = SteamGlobalStatsSensor("TEST_API_KEY", "TEST_STEAM_ID", "Stats")
        self.schema = response({"game": {}})
        self.progress = response(
            {
                "playerstats": {
                    "success": True,
                    "achievements": [{"apiname": "FIRST", "achieved": 1}],
                }
            }
        )
        self.games = [
            {"appid": 1, "name": "First", "playtime_forever": 60},
            {"appid": 2, "name": "No stats", "playtime_forever": 0},
        ]
        self.badges = response({"response": {"badges": [{"badgeid": 1}]}})
        self.requests = []
        self.http = patch(
            "custom_components.steam_tracker.sensor.requests.get",
            side_effect=self.get,
        )
        self.http.start()
        self.addCleanup(self.http.stop)

    def get(self, url, *, params, timeout):
        self.requests.append((url, params.get("appid")))
        if url == API_OWNED_GAMES:
            return response(
                {"response": {"game_count": len(self.games), "games": self.games}}
            )
        if url == API_ACHIEVEMENTS:
            if params["appid"] == 1:
                return self.progress
            return response(
                {"playerstats": {
                    "success": False, "error": "Requested app has no stats",
                }},
                400,
            )
        if url == API_SCHEMA:
            if params["appid"] == 1:
                return response({"game": {"availableGameStats": {
                    "achievements": [{"name": "FIRST"}],
                }}})
            return self.schema
        if url == API_RECENT_GAMES:
            return response(
                {"response": {"total_count": len(self.games), "games": self.games}}
            )
        if url == API_BADGES:
            return self.badges
        self.fail("Unexpected Steam endpoint")

    def test_game_without_schema_does_not_abort_library_scan(self):
        for game in (
            {},
            {"gameName": "No stats", "gameVersion": "1"},
            {"availableGameStats": {}},
            {"availableGameStats": {"achievements": []}},
        ):
            with self.subTest(game=game):
                self.schema = response({"game": game})
                self.requests.clear()
                self.sensor.update()
                self.assertTrue(self.sensor.available)
                self.assertEqual(self.sensor.native_value, 1)
                self.assertEqual(self.sensor.extra_state_attributes, {
                    "achievements_total": 1,
                    "achievements_possible": 1,
                    "perfect_games": 1,
                    "avg_completion_rate": 100.0,
                    "badge_count": 1,
                    "card_badge_count": 0,
                })
                self.assertEqual(self.requests, [
                    (API_OWNED_GAMES, None), (API_ACHIEVEMENTS, 1),
                    (API_ACHIEVEMENTS, 2), (API_SCHEMA, 2), (API_BADGES, None),
                ])

    def test_invalid_or_failed_schema_clears_values_and_recovers(self):
        cases = [
            response({}),
            response({"game": None}),
            response({"game": {"availableGameStats": None}}),
            response({"game": {"availableGameStats": []}}),
            response({"game": {"availableGameStats": {"achievements": None}}}),
            response({"game": {"availableGameStats": {
                "achievements": [{"name": "FIRST"}],
            }}}),
            response({"game": {}}, 403),
            response({"game": {}}, 500),
        ]
        for invalid in cases:
            with self.subTest(payload=invalid.content, status=invalid.status_code):
                self.schema = response({"game": {}})
                self.sensor.update()
                self.assertTrue(self.sensor.available)
                self.schema = invalid
                with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                    self.sensor.update()
                self.assertFalse(self.sensor.available)
                self.assertIsNone(self.sensor.native_value)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.schema = response({"game": {}})
                self.sensor.update()
                self.assertTrue(self.sensor.available)

    def test_private_progress_is_not_counted_as_zero(self):
        self.progress = response({"playerstats": {"success": False}}, 403)
        with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
            self.sensor.update()
        self.assertFalse(self.sensor.available)
        self.assertEqual(self.sensor.extra_state_attributes, {})
        self.assertNotIn((API_SCHEMA, 1), self.requests)

    def test_schema_verification_accepts_game_without_stats(self):
        self.assertEqual(
            self.sensor._achievement_progress(2, verify_schema=True), (0, 0)
        )

    def test_recent_achievements_includes_game_without_stats(self):
        sensor = SteamRecentAchievementsSensor("TEST_API_KEY", "TEST_STEAM_ID", "Recent")
        sensor.update()
        self.assertTrue(sensor.available)
        self.assertEqual(sensor.native_value, 2)
        game = sensor.extra_state_attributes["recent_achievements"][1]
        self.assertEqual((game["unlocked"], game["total"], game["percent"]), (0, 0, None))

    def test_top_five_games_includes_confirmed_zero_achievements(self):
        sensor = SteamPlaytimeSensor("TEST_API_KEY", "TEST_STEAM_ID", "Playtime")
        sensor.update()
        self.assertTrue(sensor.available)
        self.assertEqual(sensor.native_value, 1)
        game = sensor.extra_state_attributes["top_5_games"][1]
        self.assertEqual(game["achievements_unlocked"], 0)
        self.assertEqual(game["achievements_total"], 0)
        self.assertIsNone(game["achievements_percent"])

    def test_locked_achievements_are_valid_zero_progress(self):
        self.progress = response({"playerstats": {
            "success": True,
            "achievements": [{"apiname": "FIRST", "achieved": 0}],
        }})
        self.sensor.update()
        self.assertTrue(self.sensor.available)
        self.assertEqual(self.sensor.native_value, 0)
        self.assertEqual(self.sensor.extra_state_attributes["achievements_possible"], 1)
        self.assertEqual(self.sensor.extra_state_attributes["perfect_games"], 0)

    def test_empty_library_has_zero_totals(self):
        self.games = []
        self.sensor.update()
        self.assertTrue(self.sensor.available)
        self.assertEqual(self.sensor.native_value, 0)
        self.assertEqual(self.sensor.extra_state_attributes["perfect_games"], 0)
        self.assertEqual(self.sensor.extra_state_attributes["avg_completion_rate"], 0)
        self.assertEqual(self.requests, [(API_OWNED_GAMES, None), (API_BADGES, None)])


if __name__ == "__main__":
    unittest.main()
