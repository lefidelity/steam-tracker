"""Verify complete achievement summaries without additional Steam traffic."""

import json
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.sensor import (
    API_ACHIEVEMENTS, API_BADGES, API_OWNED_GAMES,
    SteamGlobalStatsSensor, _global_achievement_statistics,
)


def game(appid, unlocked, total, name=None):
    return {
        "appid": appid, "name": name or f"Fictional Game {appid}",
        "unlocked": unlocked, "total": total,
    }


class AchievementStatisticsTests(unittest.TestCase):
    def test_global_ratio_differs_from_equal_weight_game_average(self):
        stats = _global_achievement_statistics([game(1, 1, 1), game(2, 0, 99)])
        self.assertEqual(stats["avg_completion_rate"], 50)
        self.assertEqual(stats["overall_completion_rate"], 1)
        self.assertEqual(stats["achievements_remaining"], 99)
        self.assertEqual(stats["achievements_total"], 1)
        self.assertEqual(stats["achievements_possible"], 100)

    def test_distribution_uses_exact_ratios_before_display_rounding(self):
        progress = [
            (0, 100), (1, 1000), (24999, 100000), (25, 100), (49999, 100000),
            (50, 100), (74999, 100000), (75, 100), (99999, 100000), (100, 100),
            (0, 0),
        ]
        stats = _global_achievement_statistics([
            game(index + 1, unlocked, total)
            for index, (unlocked, total) in enumerate(progress)
        ])
        self.assertEqual(stats["completion_distribution"], {
            "not_started": 1, "under_25": 2, "25_to_50": 2,
            "50_to_75": 2, "75_to_100": 2, "complete": 1,
        })
        self.assertEqual(stats["games_with_achievements"], 10)
        self.assertEqual(stats["games_without_achievements"], 1)
        self.assertEqual(sum(stats["completion_distribution"].values()), 10)
        self.assertEqual(stats["perfect_games"], 1)
        self.assertIn(9, [item["appid"] for item in stats["completion_candidates"]])

    def test_candidates_rank_remaining_then_progress_name_and_appid(self):
        games = [
            game(8, 1, 10), game(7, 0, 0), game(6, 5, 5),
            game(5, 0, 1), game(4, 8, 10), game(3, 9, 10),
            game(2, 99, 100, "Beta"), game(1, 99, 100, "alpha"),
            game(10, 99, 100, "ALPHA"),
        ]
        original = [dict(item) for item in games]
        candidates = _global_achievement_statistics(games)["completion_candidates"]
        self.assertEqual([item["appid"] for item in candidates], [1, 10, 2, 3, 5])
        self.assertEqual(candidates[0], {
            "appid": 1, "name": "alpha", "unlocked": 99, "total": 100,
            "remaining": 1, "percent": 99,
        })
        self.assertEqual(games, original)

    def test_empty_no_achievement_and_completed_libraries(self):
        for games, without in (([], 0), ([game(1, 0, 0)], 1)):
            with self.subTest(games=games):
                stats = _global_achievement_statistics(games)
                self.assertEqual(stats["achievements_remaining"], 0)
                self.assertIsNone(stats["overall_completion_rate"])
                self.assertEqual(stats["completion_candidates"], [])
                self.assertEqual(stats["games_without_achievements"], without)
                self.assertEqual(sum(stats["completion_distribution"].values()), 0)
        stats = _global_achievement_statistics([game(1, 2, 2)])
        self.assertEqual(stats["overall_completion_rate"], 100)
        self.assertEqual(stats["completion_candidates"], [])

    def test_real_scan_has_unchanged_request_budget_and_clears_partial_statistics(self):
        sensor = SteamGlobalStatsSensor("TEST_API_KEY", "TEST_STEAM_ID", "Stats")
        failure = False
        calls = []

        def get(url, *, params, timeout):
            calls.append((url, params.get("appid")))
            status = 200
            if url == API_OWNED_GAMES:
                payload = {"response": {"game_count": 2, "games": [
                    {"appid": 1, "name": "Fictional Complete"},
                    {"appid": 2, "name": "Fictional Candidate"},
                ]}}
            elif url == API_ACHIEVEMENTS:
                payload = {"playerstats": {"success": True, "achievements": [
                    {"apiname": "FIRST", "achieved": int(params["appid"] == 1)},
                ]}}
                if failure and params["appid"] == 2:
                    status = 503
            elif url == API_BADGES:
                payload = {"response": {"badges": []}}
            else:
                self.fail("Unexpected additional Steam request")
            response = requests.Response()
            response.status_code = status
            response._content = json.dumps(payload).encode()
            return response

        with patch("custom_components.steam_tracker.sensor.requests.get", side_effect=get):
            for recovering in (False, True):
                failure = False
                calls.clear()
                sensor.update()
                self.assertTrue(sensor.available)
                self.assertEqual(calls, [
                    (API_OWNED_GAMES, None), (API_ACHIEVEMENTS, 1),
                    (API_ACHIEVEMENTS, 2), (API_BADGES, None),
                ])
                self.assertEqual(sensor.extra_state_attributes["overall_completion_rate"], 50)
                self.assertEqual(sensor.extra_state_attributes["completion_candidates"][0]["appid"], 2)
                if not recovering:
                    failure = True
                    with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                        sensor.update()
                    self.assertFalse(sensor.available)
                    self.assertIsNone(sensor.native_value)
                    self.assertEqual(sensor.extra_state_attributes, {})


if __name__ == "__main__":
    unittest.main()
