"""Keep unavailable friend presence distinct from confirmed offline status."""

import json
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.sensor import (
    API_FRIENDS, API_SUMMARIES, SteamFriendsSensor,
)


class FriendsTests(unittest.TestCase):
    def setUp(self):
        self.sensor = SteamFriendsSensor("TEST_API_KEY", "TEST_STEAM_ID", "Friends")
        self.players = [{"steamid": "TEST_FRIEND_A", "personaname": "Fictional Friend"}]
        self.summary_status = 200
        self.calls = []

        def get(url, *, params, timeout):
            self.calls.append((url, params, timeout))
            status = 200
            if url == API_FRIENDS:
                payload = {"friendslist": {"friends": [{"steamid": "TEST_FRIEND_A"}]}}
            elif url == API_SUMMARIES:
                payload = {"response": {"players": self.players}}
                status = self.summary_status
            else:
                self.fail("Unexpected Steam endpoint")
            response = requests.Response()
            response.status_code = status
            response._content = json.dumps(payload).encode()
            return response

        http = patch("custom_components.steam_tracker.sensor.requests.get", side_effect=get)
        http.start()
        self.addCleanup(http.stop)

    def assert_presence(self, expected):
        self.calls.clear()
        self.sensor.update()
        self.assertTrue(self.sensor.available)
        self.assertEqual(self.sensor.native_value, 1)
        friend = self.sensor.extra_state_attributes["friends"][0]
        self.assertEqual(friend["status"], expected)
        self.assertEqual(friend["personaname"], "Fictional Friend")
        self.assertEqual(friend["steamid"], "TEST_FRIEND_A")
        self.assertIn("last_successful_update", self.sensor.extra_state_attributes)
        self.assertEqual([call[0] for call in self.calls], [API_FRIENDS, API_SUMMARIES])
        self.assertTrue(all(call[2] == 15 for call in self.calls))

    def test_missing_presence_is_unknown(self):
        self.assert_presence("Unknown")

    def test_invalid_presence_is_unknown_without_invalidating_the_friends_list(self):
        for value in (None, False, True, 0.0, 1.0, "0", "1", -1, 7, [], {}):
            with self.subTest(value=value):
                self.players[0]["personastate"] = value
                self.assert_presence("Unknown")

    def test_valid_integer_statuses_keep_their_existing_meaning(self):
        for value, status in enumerate((
            "Offline", "Online", "Busy", "Away", "Snooze",
            "Looking to trade", "Looking to play",
        )):
            with self.subTest(value=value):
                self.players[0]["personastate"] = value
                self.assert_presence(status)

    def test_presence_transitions_never_reuse_a_previous_known_status(self):
        self.players[0]["personastate"] = 1
        self.assert_presence("Online")
        del self.players[0]["personastate"]
        self.assert_presence("Unknown")
        self.players[0]["personastate"] = 0
        self.assert_presence("Offline")

    def test_failed_or_incomplete_summaries_still_clear_data_and_recover(self):
        for failure in ("http", "missing_friend"):
            with self.subTest(failure=failure):
                self.assert_presence("Unknown")
                if failure == "http":
                    self.summary_status = 503
                else:
                    self.players = []
                with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
                    self.sensor.update()
                self.assertFalse(self.sensor.available)
                self.assertIsNone(self.sensor.native_value)
                self.assertEqual(self.sensor.extra_state_attributes, {})
                self.summary_status = 200
                self.players = [{"steamid": "TEST_FRIEND_A", "personaname": "Fictional Friend"}]
                self.assert_presence("Unknown")


if __name__ == "__main__":
    unittest.main()
