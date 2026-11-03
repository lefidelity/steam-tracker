"""Check library metrics against raw Steam minutes without network access."""

import json
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.sensor import (
    API_ACHIEVEMENTS,
    API_OWNED_GAMES,
    SteamPlaytimeSensor,
)


def response(payload):
    result = requests.Response()
    result.status_code = 200
    result._content = json.dumps(payload).encode()
    return result


class LibraryStatisticsTests(unittest.TestCase):
    """Exercise full playtime updates and the existing request budget."""

    def setUp(self):
        self.sensor = SteamPlaytimeSensor("TEST_API_KEY", "TEST_STEAM_ID", "Playtime")
        self.owned = {}
        self.achievement_failure = False
        self.calls = []
        mock_http = patch(
            "custom_components.steam_tracker.sensor.requests.get", side_effect=self.get
        )
        mock_http.start()
        self.addCleanup(mock_http.stop)

    def get(self, url, *, params, timeout):
        self.calls.append(url)
        if url == API_OWNED_GAMES:
            return response({"response": self.owned})
        if url == API_ACHIEVEMENTS:
            if self.achievement_failure:
                raise requests.ReadTimeout()
            return response({"playerstats": {
                "success": True,
                "achievements": [{"apiname": "FIRST", "achieved": 0}],
            }})
        self.fail("Unexpected additional API request")

    def refresh(self, minutes):
        self.owned = {
            "game_count": len(minutes),
            "games": [
                {"appid": index, "name": f"Game {index:02}", "playtime_forever": value}
                for index, value in enumerate(minutes, 1)
            ],
        }
        self.calls.clear()
        self.sensor.update()
        self.assertTrue(self.sensor.available)
        self.assertEqual(
            self.calls, [API_OWNED_GAMES] + [API_ACHIEVEMENTS] * min(5, len(minutes))
        )
        return self.sensor.extra_state_attributes

    def test_distribution_boundaries_and_top_five_share(self):
        attrs = self.refresh([0, 1, 59, 60, 599, 600, 2999, 3000])
        self.assertEqual(attrs["game_count"], 8)
        self.assertEqual(attrs["played_game_count"], 7)
        self.assertEqual(attrs["unplayed_game_count"], 1)
        self.assertEqual(attrs["unplayed_games"], [{"appid": 1, "name": "Game 01"}])
        self.assertEqual(attrs["played_percentage"], 87.5)
        self.assertEqual(attrs["top_5_playtime_percentage"], 99.2)
        self.assertEqual(attrs["playtime_distribution"], {
            "unplayed": 1, "under_1_hour": 2, "1_to_10_hours": 2,
            "10_to_50_hours": 2, "50_hours_or_more": 1,
        })
        self.assertEqual(sum(attrs["playtime_distribution"].values()), 8)
        self.assertEqual(attrs["pile_of_shame_count"], 3)
        self.assertEqual(self.sensor.native_value, 122.0)

    def test_short_sessions_use_minutes_even_when_hours_round_to_zero(self):
        for minutes in (1, 2):
            with self.subTest(minutes=minutes):
                attrs = self.refresh([0, minutes])
                self.assertEqual([game["hours"] for game in attrs["all_games"]], [0, 0])
                self.assertEqual(self.sensor.native_value, 0)
                self.assertEqual(attrs["played_percentage"], 50)
                self.assertEqual(attrs["unplayed_game_count"], 1)
                self.assertEqual(attrs["top_5_playtime_percentage"], 100)

    def test_empty_library_has_empty_lists_and_zero_percentages(self):
        self.refresh([60])
        self.owned = {"game_count": 0}
        self.calls.clear()
        self.sensor.update()
        self.assertTrue(self.sensor.available)
        attrs = self.sensor.extra_state_attributes
        self.assertEqual(self.sensor.native_value, 0)
        self.assertEqual(attrs["played_game_count"], 0)
        self.assertEqual(attrs["unplayed_game_count"], 0)
        self.assertEqual(attrs["unplayed_games"], [])
        self.assertEqual(attrs["played_percentage"], 0)
        self.assertEqual(attrs["top_5_playtime_percentage"], 0)
        self.assertEqual(list(attrs["playtime_distribution"].values()), [0] * 5)
        self.assertEqual(self.calls, [API_OWNED_GAMES])

    def test_all_unplayed_games_are_sorted_by_name(self):
        attrs = self.refresh([0, 0])
        self.owned["games"].reverse()
        self.sensor.update()
        self.assertEqual(self.sensor.extra_state_attributes["unplayed_games"],
                         [{"appid": 1, "name": "Game 01"},
                          {"appid": 2, "name": "Game 02"}])
        self.assertEqual(attrs["played_percentage"], 0)
        self.assertEqual(attrs["top_5_playtime_percentage"], 0)
        self.assertEqual(attrs["unplayed_game_count"], 2)

    def test_missing_or_invalid_minutes_clear_stats_and_recover(self):
        for value in (None, True, -1, 1.5, "60", "missing"):
            with self.subTest(value=value):
                self.refresh([60])
                game = self.owned["games"][0]
                if value == "missing":
                    del game["playtime_forever"]
                else:
                    game["playtime_forever"] = value
                with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                    self.sensor.update()
                self.assertFalse(self.sensor.available)
                self.assertIsNone(self.sensor.native_value)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.refresh([0, 60])

    def test_achievement_timeout_keeps_library_statistics_available(self):
        self.achievement_failure = True
        with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
            attrs = self.refresh([0, 60])
        self.assertEqual(attrs["played_percentage"], 50)
        self.assertEqual(attrs["unplayed_game_count"], 1)
        self.assertIsNone(attrs["top_5_games"][0]["achievements_unlocked"])


if __name__ == "__main__":
    unittest.main()
