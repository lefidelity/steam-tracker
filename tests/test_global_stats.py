"""Regression checks for library-wide achievement scans with mocked Steam HTTP."""

import json
import unittest
from unittest.mock import ANY, patch

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
                    "achievements_remaining": 0,
                    "overall_completion_rate": 100.0,
                    "games_with_achievements": 1,
                    "games_without_achievements": 1,
                    "completion_distribution": {
                        "not_started": 0, "under_25": 0, "25_to_50": 0,
                        "50_to_75": 0, "75_to_100": 0, "complete": 1,
                    },
                    "completion_candidates": [],
                    "last_successful_update": ANY,
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
        for status in (401, 403, 429, 502, 503, 504):
            with self.subTest(status=status):
                self.requests.clear()
                self.progress = response({"playerstats": {"success": False}}, status)
                with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                    self.sensor.update()
                self.assertFalse(self.sensor.available)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.assertNotIn((API_SCHEMA, 1), self.requests)

    def test_http_failures_identify_stage_without_leaking_request_data(self):
        cases = (
            (API_OWNED_GAMES, None, "GetOwnedGames/v1", 1),
            (API_ACHIEVEMENTS, 1, "GetPlayerAchievements/v1, appid=1", 3),
            (API_SCHEMA, 2, "GetSchemaForGame/v2, appid=2", 4),
            (API_BADGES, None, "GetBadges/v1", 5),
        )
        for endpoint, appid, context, request_count in cases:
            with self.subTest(context=context):
                self.sensor.update()
                self.assertTrue(self.sensor.available)
                self.requests.clear()

                def fail_request(url, *, params, timeout):
                    result = self.get(url, params=params, timeout=timeout)
                    if url == endpoint and params.get("appid") == appid:
                        result = response({}, 500)
                        result.url = f"{url}?key=SECRET_KEY&steamid=PRIVATE_ACCOUNT"
                        result.reason = "UNTRUSTED_SERVER_TEXT"
                    return result

                with patch(
                    "custom_components.steam_tracker.sensor.requests.get",
                    side_effect=fail_request,
                ), self.assertLogs(
                    "custom_components.steam_tracker.sensor", "ERROR"
                ) as logs:
                    self.sensor.update()

                self.assertEqual(len(logs.output), 1)
                self.assertIn(
                    f"Error fetching global stats [{context}] (HTTPError, HTTP 500)",
                    logs.output[0],
                )
                for secret in (
                    "SECRET_KEY", "PRIVATE_ACCOUNT", "UNTRUSTED_SERVER_TEXT",
                    "https://", "TEST_API_KEY", "TEST_STEAM_ID",
                ):
                    self.assertNotIn(secret, logs.output[0])
                self.assertFalse(self.sensor.available)
                self.assertIsNone(self.sensor.native_value)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.assertEqual(len(self.requests), request_count)
                self.sensor.update()
                self.assertTrue(self.sensor.available)

    def test_achievement_transport_and_validation_errors_keep_safe_context(self):
        for failure in (
            requests.ReadTimeout("SECRET_KEY in https://private.example/"),
            ValueError("SECRET_KEY in untrusted response"),
        ):
            with self.subTest(error=type(failure).__name__):
                def fail_request(url, *, params, timeout):
                    if url == API_ACHIEVEMENTS:
                        raise failure
                    return self.get(url, params=params, timeout=timeout)

                with patch(
                    "custom_components.steam_tracker.sensor.requests.get",
                    side_effect=fail_request,
                ), self.assertLogs(
                    "custom_components.steam_tracker.sensor", "ERROR"
                ) as logs:
                    self.sensor.update()
                self.assertIn(
                    f"[GetPlayerAchievements/v1, appid=1] ({type(failure).__name__})",
                    logs.output[0],
                )
                self.assertNotIn("SECRET_KEY", logs.output[0])
                self.assertNotIn("https://", logs.output[0])
                self.assertFalse(self.sensor.available)

    def test_http_500_without_achievements_requires_confirmed_empty_schema(self):
        for sensor_type in (
            SteamGlobalStatsSensor, SteamRecentAchievementsSensor, SteamPlaytimeSensor
        ):
            with self.subTest(sensor=sensor_type.__name__):
                sensor = sensor_type("TEST_API_KEY", "TEST_STEAM_ID", "Stats")

                def fail_no_stats_request(url, *, params, timeout):
                    if url == API_ACHIEVEMENTS and params["appid"] == 2:
                        self.requests.append((url, 2))
                        return response({"error": "UNTRUSTED_SERVER_TEXT"}, 500)
                    return self.get(url, params=params, timeout=timeout)

                self.requests.clear()
                with patch(
                    "custom_components.steam_tracker.sensor.requests.get",
                    side_effect=fail_no_stats_request,
                ):
                    sensor.update()
                self.assertTrue(sensor.available)
                self.assertEqual(self.requests.count((API_ACHIEVEMENTS, 2)), 1)
                self.assertEqual(self.requests.count((API_SCHEMA, 2)), 1)
                if sensor_type is SteamGlobalStatsSensor:
                    self.assertEqual(sensor.native_value, 1)
                    self.assertEqual(sensor.extra_state_attributes["achievements_possible"], 1)
                    self.assertEqual(sensor.extra_state_attributes["perfect_games"], 1)
                else:
                    key = (
                        "recent_achievements"
                        if sensor_type is SteamRecentAchievementsSensor
                        else "top_5_games"
                    )
                    game = sensor.extra_state_attributes[key][1]
                    if sensor_type is SteamRecentAchievementsSensor:
                        progress = (game["unlocked"], game["total"], game["percent"])
                    else:
                        progress = (
                            game["achievements_unlocked"], game["achievements_total"],
                            game["achievements_percent"],
                        )
                    self.assertEqual(progress, (0, 0, None))

    def test_http_500_with_failed_or_nonempty_schema_never_publishes_partial_totals(self):
        schemas = (
            response({}),
            response({"game": None}),
            response({"game": {"availableGameStats": None}}),
            response({"game": {"availableGameStats": {"achievements": None}}}),
            response({"game": {}}, 500),
            response({"game": {}}, 403),
            response({"game": {"availableGameStats": {
                "achievements": [{"name": "UNKNOWN_PROGRESS"}],
            }}}),
        )
        for schema in schemas:
            with self.subTest(status=schema.status_code, payload=schema.content):
                self.sensor.update()
                self.assertTrue(self.sensor.available)
                self.schema = schema

                def fail_no_stats_request(url, *, params, timeout):
                    if url == API_ACHIEVEMENTS and params["appid"] == 2:
                        return response({}, 500)
                    return self.get(url, params=params, timeout=timeout)

                with patch(
                    "custom_components.steam_tracker.sensor.requests.get",
                    side_effect=fail_no_stats_request,
                ), self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                    self.sensor.update()
                self.assertFalse(self.sensor.available)
                self.assertIsNone(self.sensor.native_value)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.schema = response({"game": {}})
                self.sensor.update()
                self.assertTrue(self.sensor.available)

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
