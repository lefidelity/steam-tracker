"""Exercise account-scoped summary reuse without any Steam connections."""

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from threading import Event
import unittest
from unittest.mock import patch

import requests

from custom_components.steam_tracker.api import (
    API_PLAYER_SUMMARIES,
    PLAYER_SUMMARY_CACHE_SECONDS,
    SteamAccountNotFound,
    SteamAuthError,
    SteamConnectionError,
    SteamPlayerSummaryCache,
    SteamResponseError,
)
from custom_components.steam_tracker.sensor import API_OWNED_GAMES, _create_entities, setup_platform


KEY = "TEST_API_KEY"
STEAM_ID = "TEST_STEAM_ID"
PLAYER = {"steamid": STEAM_ID, "personastate": 1, "communityvisibilitystate": 3}


def response(player=None, *, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps({"response": {"players": [player or PLAYER]}}).encode()
    return result


class PlayerSummaryCacheTests(unittest.TestCase):
    """Check TTL, simultaneous requests, retries, timestamps, and isolation."""

    def setUp(self):
        self.seconds = 1000.0
        self.fetched_at = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
        self.http_patch = patch("requests.get", return_value=response())
        self.http = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.timer_patch = patch(
            "custom_components.steam_tracker.api.monotonic", side_effect=lambda: self.seconds
        )
        self.timer_patch.start()
        self.addCleanup(self.timer_patch.stop)
        self.clock_patch = patch("custom_components.steam_tracker.api.datetime")
        self.clock = self.clock_patch.start()
        self.clock.now.side_effect = lambda zone: self.fetched_at
        self.addCleanup(self.clock_patch.stop)
        self.cache = SteamPlayerSummaryCache(KEY, STEAM_ID)

    def test_hits_keep_original_data_and_timestamp_until_exact_expiry(self):
        first = self.cache.get()
        self.http.assert_called_once()
        self.assertEqual(first.fetched_at, self.fetched_at.isoformat())
        self.seconds += PLAYER_SUMMARY_CACHE_SECONDS - 0.001
        self.fetched_at += timedelta(hours=1)
        self.assertEqual(self.cache.get(), first)
        self.http.assert_called_once()
        self.seconds = 1000.0 + PLAYER_SUMMARY_CACHE_SECONDS
        second = self.cache.get()
        self.assertEqual(self.http.call_count, 2)
        self.assertEqual(second.player, first.player)
        self.assertNotEqual(second.fetched_at, first.fetched_at)

    def test_expiry_starts_after_a_slow_fetch_completes(self):
        def slow_get(*args, **kwargs):
            self.seconds += 30
            return response()

        self.http.side_effect = slow_get
        first = self.cache.get()
        self.seconds += PLAYER_SUMMARY_CACHE_SECONDS - 1
        self.assertEqual(self.cache.get(), first)
        self.http.assert_called_once()

    def test_returned_player_data_cannot_change_other_consumers(self):
        self.http.return_value = response({**PLAYER, "nested": {"name": "Original"}})
        first = self.cache.get()
        first.player["personastate"] = 0
        first.player["nested"]["name"] = "Changed"
        second = self.cache.get()
        self.assertEqual(second.player["personastate"], 1)
        self.assertEqual(second.player["nested"]["name"], "Original")
        self.assertIsNot(first.player, second.player)
        self.http.assert_called_once()

    def parallel_fetches(self, error=None):
        started, waiting, release = Event(), Event(), Event()

        class PendingResult(Future):
            def result(self, timeout=None):
                waiting.set()
                return super().result(timeout)

        def get(*args, **kwargs):
            started.set()
            if not release.wait(5):
                raise AssertionError("Test did not release the mocked HTTP response")
            if error is not None:
                raise error
            return response()

        self.http.side_effect = get
        with patch("custom_components.steam_tracker.api.Future", PendingResult):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(self.cache.get)
                second = None
                try:
                    self.assertTrue(started.wait(5))
                    second = executor.submit(self.cache.get)
                    self.assertTrue(waiting.wait(5), "Second reader must join the pending fetch")
                    self.http.assert_called_once()
                finally:
                    release.set()
                if error is None:
                    results = first.result(5), second.result(5)
                    self.assertEqual(*results)
                    self.assertIsNot(results[0].player, results[1].player)
                else:
                    for pending in (first, second):
                        with self.assertRaises(SteamConnectionError):
                            pending.result(5)
        self.http.assert_called_once()

    def test_simultaneous_readers_share_one_network_fetch(self):
        self.parallel_fetches()

    def test_simultaneous_failure_is_shared_but_next_attempt_retries(self):
        self.parallel_fetches(requests.ReadTimeout())
        self.http.side_effect = None
        result = self.cache.get()
        self.assertEqual(result.player, PLAYER)
        self.assertEqual(self.http.call_count, 2)

    def test_failed_or_invalid_fetch_never_serves_expired_data_and_recovers(self):
        empty = response()
        empty._content = b'{"response":{"players":[]}}'
        malformed = response()
        malformed._content = b'not json'
        for reply, error in (
            (requests.ReadTimeout(), SteamConnectionError),
            (response(status=403), SteamAuthError),
            (response(status=500), SteamConnectionError),
            (malformed, SteamResponseError),
            (empty, SteamAccountNotFound),
            (response({"steamid": "ANOTHER_TEST_ID"}), SteamResponseError),
        ):
            with self.subTest(error=error, reply=type(reply)):
                self.http.side_effect = None
                self.http.return_value = response()
                first = self.cache.get()
                self.seconds += PLAYER_SUMMARY_CACHE_SECONDS
                self.fetched_at += timedelta(minutes=1)
                self.http.side_effect = reply if isinstance(reply, Exception) else None
                self.http.return_value = reply
                with self.assertRaises(error):
                    self.cache.get()
                self.http.side_effect = None
                self.http.return_value = response({**PLAYER, "personastate": 0})
                recovered = self.cache.get()
                self.assertEqual(recovered.player["personastate"], 0)
                self.assertNotEqual(recovered.fetched_at, first.fetched_at)

    def test_accounts_and_replacement_keys_never_share_cached_data(self):
        self.cache.get()
        other = SteamPlayerSummaryCache(KEY, "OTHER_TEST_ID")
        self.http.return_value = response({**PLAYER, "steamid": "OTHER_TEST_ID"})
        self.assertEqual(other.get().player["steamid"], "OTHER_TEST_ID")
        replacement = SteamPlayerSummaryCache("REPLACEMENT_TEST_KEY", STEAM_ID)
        self.http.return_value = response({**PLAYER, "personastate": 0})
        self.assertEqual(replacement.get().player["personastate"], 0)
        self.assertEqual(self.cache.get().player["personastate"], 1)
        self.assertEqual(self.http.call_count, 3)
        self.assertEqual(self.http.call_args.kwargs["headers"], {"x-webapi-key": "REPLACEMENT_TEST_KEY"})

    def test_incomplete_sensor_fields_do_not_delay_a_fresh_retry(self):
        for player in (
            {"steamid": STEAM_ID},
            {**PLAYER, "personastate": True},
            {**PLAYER, "gameextrainfo": "Fictional Game"},
        ):
            with self.subTest(player=player):
                cache = SteamPlayerSummaryCache(KEY, STEAM_ID)
                self.http.reset_mock()
                self.http.return_value = response(player)
                cache.get()
                self.http.return_value = response()
                self.assertEqual(cache.get().player, PLAYER)
                self.assertEqual(self.http.call_count, 2)

    def test_a_slow_account_does_not_block_another_account(self):
        started, release = Event(), Event()

        def get(url, *, params, **kwargs):
            steam_id = params["steamids"]
            if steam_id == STEAM_ID:
                started.set()
                if not release.wait(5):
                    raise AssertionError("Mocked first account was not released")
            return response({**PLAYER, "steamid": steam_id})

        self.http.side_effect = get
        other = SteamPlayerSummaryCache(KEY, "OTHER_TEST_ID")
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(self.cache.get)
            try:
                self.assertTrue(started.wait(5))
                second = executor.submit(other.get)
                self.assertEqual(second.result(5).player["steamid"], "OTHER_TEST_ID")
            finally:
                release.set()
            self.assertEqual(first.result(5).player["steamid"], STEAM_ID)

    def test_factory_shares_only_status_and_game_and_keeps_fetch_timestamp(self):
        entities = _create_entities(KEY, STEAM_ID, "Test")
        status, game = entities[:2]
        self.assertIs(status._player_summary_cache, game._player_summary_cache)
        self.assertTrue(all(entity._player_summary_cache is None for entity in entities[2:]))
        status.update()
        first = status.extra_state_attributes["last_successful_update"]
        self.fetched_at += timedelta(seconds=10)
        game.update()
        self.assertTrue(status.available)
        self.assertTrue(game.available)
        self.assertEqual(game.native_value, "none")
        self.assertEqual(game.extra_state_attributes["last_successful_update"], first)
        self.http.assert_called_once()
        self.seconds += PLAYER_SUMMARY_CACHE_SECONDS
        self.http.return_value = response(status=403)
        with self.assertLogs("custom_components.steam_tracker.sensor", "ERROR"):
            game.update()
        self.assertFalse(game.available)
        self.assertEqual(game.extra_state_attributes, {})
        self.http.return_value = response()
        game.update()
        self.assertTrue(game.available)
        self.assertNotEqual(game.extra_state_attributes["last_successful_update"], first)

    def test_current_game_playtime_is_not_cached_with_player_summaries(self):
        player = {**PLAYER, "gameid": "1", "gameextrainfo": "Fictional Game"}
        owned = response()
        owned._content = b'{"response":{"game_count":1,"games":[{"appid":1,"playtime_forever":60}]}}'
        self.http.side_effect = [response(player), owned, owned]
        status, game = _create_entities(KEY, STEAM_ID, "Test")[:2]
        status.update()
        game.update()
        self.fetched_at += timedelta(seconds=10)
        game.update()
        self.assertTrue(game.available)
        self.assertEqual(game.extra_state_attributes["total_playtime_hours"], 1)
        self.assertEqual(game.extra_state_attributes["last_successful_update"], status.extra_state_attributes["last_successful_update"])
        self.assertEqual([call.args[0] for call in self.http.call_args_list], [API_PLAYER_SUMMARIES, API_OWNED_GAMES, API_OWNED_GAMES])

    def test_legacy_yaml_shares_a_cache_and_a_new_setup_starts_empty(self):
        entities = []
        config = {"api_key": KEY, "steam_id": STEAM_ID, "name": "Test"}
        setup_platform(None, config, entities.extend)
        entities[0].update()
        entities[1].update()
        self.http.assert_called_once()
        replacement = []
        setup_platform(None, config, replacement.extend)
        self.assertIsNot(replacement[0]._player_summary_cache, entities[0]._player_summary_cache)
        replacement[0].update()
        self.assertEqual(self.http.call_count, 2)


if __name__ == "__main__":
    unittest.main()
