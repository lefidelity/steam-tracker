"""Verify timestamps represent complete, successful sensor fetches only."""

from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.sensor import (
    API_ACHIEVEMENTS, API_BADGES, API_FRIENDS, API_OWNED_GAMES,
    API_RECENT_GAMES, API_SCHEMA, API_SUMMARIES, API_URL, _create_entities,
)


def response(payload):
    result = requests.Response()
    result.status_code = 200
    result._content = json.dumps(payload).encode()
    return result


class DataFreshnessTests(unittest.TestCase):
    """Exercise all eight sensors and their empty and failed update paths."""

    def setUp(self):
        self.empty = False
        self.calls = []
        self.now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
        self.entities = _create_entities("TEST_API_KEY", "TEST_STEAM_ID", "Test")
        self.http_patch = patch("requests.get", side_effect=self.get)
        self.http = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.clock_patch = patch("custom_components.steam_tracker.sensor.datetime")
        self.clock = self.clock_patch.start()
        self.clock.now.side_effect = lambda zone: self.now + timedelta(seconds=len(self.calls))
        self.addCleanup(self.clock_patch.stop)
        self.api_clock_patch = patch(
            "custom_components.steam_tracker.api.datetime", self.clock
        )
        self.api_clock_patch.start()
        self.addCleanup(self.api_clock_patch.stop)
        self.cache_time = 0
        self.cache_time_patch = patch(
            "custom_components.steam_tracker.api.monotonic", side_effect=lambda: self.cache_time
        )
        self.cache_time_patch.start()
        self.addCleanup(self.cache_time_patch.stop)

    def get(self, url, **kwargs):
        self.calls.append(url)
        game = {"appid": 1, "name": "Fictional Game", "playtime_forever": 60}
        if url == API_URL:
            player = {"steamid": "TEST_STEAM_ID", "personastate": 1, "communityvisibilitystate": 3}
            if not self.empty:
                player.update(gameid="1", gameextrainfo="Fictional Game")
            return response({"response": {"players": [player]}})
        if url in (API_OWNED_GAMES, API_RECENT_GAMES):
            count_key = "game_count" if url == API_OWNED_GAMES else "total_count"
            return response({"response": {count_key: 0 if self.empty else 1, "games": [] if self.empty else [game]}})
        if url == API_ACHIEVEMENTS:
            return response({"playerstats": {"success": True, "achievements": [{"apiname": "FIRST", "achieved": 1}]}})
        if url == API_SCHEMA:
            return response({"game": {"availableGameStats": {"achievements": [{"name": "FIRST"}]}}})
        if url == API_BADGES:
            return response({"response": {"player_level": 1, "player_xp": 100,
                "player_xp_needed_to_level_up": 100, "player_xp_needed_current_level": 100, "badges": []}})
        if url == API_FRIENDS:
            return response({"friendslist": {"friends": [] if self.empty else [{"steamid": "TEST_FRIEND"}]}})
        if url == API_SUMMARIES:
            return response({"response": {"players": [{"steamid": "TEST_FRIEND", "personastate": 0}]}})
        self.fail("Unexpected Steam endpoint")

    def refresh(self, sensor):
        self.cache_time += 60
        self.calls.clear()
        self.clock.now.reset_mock()
        sensor.update()
        self.assertTrue(sensor.available)
        timestamp = sensor.extra_state_attributes["last_successful_update"]
        # Current-game playtime is supplementary; the shared summary is its source.
        source_call = 1 if sensor.sensor_type == "game" else len(self.calls)
        self.assertEqual(datetime.fromisoformat(timestamp), self.now + timedelta(seconds=source_call))
        self.clock.now.assert_called_once_with(timezone.utc)
        return timestamp

    def test_every_sensor_records_fetch_completion_without_extra_requests(self):
        counts = {"status": 1, "game": 2, "playtime": 2, "profile": 1,
            "recent_games": 1, "recent_achievements": 3, "global_stats": 3, "friends": 2}
        for sensor in self.entities:
            with self.subTest(sensor=sensor.sensor_type):
                self.assertNotIn("last_successful_update", sensor.extra_state_attributes)
                first = self.refresh(sensor)
                self.assertEqual(len(self.calls), counts[sensor.sensor_type])
                state = sensor.native_value
                self.now += timedelta(minutes=5)
                second = self.refresh(sensor)
                self.assertNotEqual(first, second)
                self.assertEqual(sensor.native_value, state)

    def test_confirmed_empty_results_are_successful_fetches(self):
        self.empty = True
        for sensor in self.entities:
            with self.subTest(sensor=sensor.sensor_type):
                self.refresh(sensor)
                self.assertEqual(len(self.calls), 2 if sensor.sensor_type == "global_stats" else 1)

    def test_failures_clear_timestamp_and_recovery_records_a_new_fetch(self):
        for sensor in self.entities:
            with self.subTest(sensor=sensor.sensor_type):
                first = self.refresh(sensor)
                for failure in (requests.ReadTimeout(), response({})):
                    self.cache_time += 60
                    self.http.side_effect = failure if isinstance(failure, Exception) else None
                    self.http.return_value = failure
                    self.clock.now.reset_mock()
                    with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                        sensor.update()
                    self.assertFalse(sensor.available)
                    self.assertEqual(sensor.extra_state_attributes, {})
                    self.clock.now.assert_not_called()
                self.http.side_effect = self.get
                self.now += timedelta(minutes=5)
                self.assertNotEqual(first, self.refresh(sensor))

    def test_incomplete_global_scan_never_records_success(self):
        sensor = next(entity for entity in self.entities if entity.sensor_type == "global_stats")
        self.refresh(sensor)

        def partial_failure(url, **kwargs):
            if url == API_BADGES:
                raise requests.ReadTimeout()
            return self.get(url, **kwargs)

        self.http.side_effect = partial_failure
        self.clock.now.reset_mock()
        with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
            sensor.update()
        self.assertFalse(sensor.available)
        self.assertNotIn("last_successful_update", sensor.extra_state_attributes)
        self.clock.now.assert_not_called()


if __name__ == "__main__":
    unittest.main()
