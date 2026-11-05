"""Check Steam access, key replacement, and reauthentication with mocked HTTP."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow

from custom_components.steam_tracker.api import (
    API_PLAYER_SUMMARIES,
    SteamAccountNotFound,
    SteamAuthError,
    SteamConnectionError,
    SteamResponseError,
    fetch_player_summary,
)
from custom_components.steam_tracker.config_flow import SteamTrackerConfigFlow
from custom_components.steam_tracker.const import DOMAIN
from custom_components.steam_tracker.sensor import (
    SteamGameSensor, SteamStatusSensor, async_setup_entry as async_setup_sensors,
)


STEAM_ID = "10000000000000001"  # Fictional test account, never sent to Steam.
OTHER_ID = "10000000000000002"
KEY = "TEST_API_KEY"
NEW_KEY = "REPLACEMENT_TEST_KEY"
PLAYER = {"steamid": STEAM_ID, "personastate": 1, "communityvisibilitystate": 3}
DATA = {"steam_id": STEAM_ID, "api_key": KEY, "name": "Fictional Account"}


def response(payload=None, status=200):
    """Build a real requests response without making a connection."""
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode()
    return result


class PlayerAccessTests(unittest.TestCase):
    """Exercise response validation and credential handling at the HTTP boundary."""

    def test_private_account_and_header_only_credentials(self):
        player = {"steamid": STEAM_ID, "communityvisibilitystate": 1}
        with patch("requests.get", return_value=response({"response": {"players": [player]}})) as get:
            self.assertEqual(fetch_player_summary(KEY, STEAM_ID), player)
        get.assert_called_once_with(
            API_PLAYER_SUMMARIES,
            params={"steamids": STEAM_ID},
            headers={"x-webapi-key": KEY},
            timeout=10,
            allow_redirects=False,
        )

    def test_http_denials_are_distinct_from_connection_failures(self):
        for status in (401, 403, 302, 404, 429, 500, 503):
            with self.subTest(status=status), patch("requests.get", return_value=response(status=status)):
                expected = SteamAuthError if status in (401, 403) else SteamConnectionError
                with self.assertRaises(expected):
                    fetch_player_summary(KEY, STEAM_ID)

    def test_network_errors_do_not_expose_request_details(self):
        for error in (requests.ReadTimeout, requests.ConnectionError):
            with self.subTest(error=error), patch("requests.get", side_effect=error(f"https://example.invalid/?key={KEY}")):
                with self.assertRaises(SteamConnectionError) as caught:
                    fetch_player_summary(KEY, STEAM_ID)
                self.assertNotIn(KEY, str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_missing_invalid_and_mismatched_players(self):
        for payload in (
            None, [], {}, {"response": []}, {"response": {}},
            {"response": {"players": None}},
            {"response": {"players": [{}]}},
            {"response": {"players": [{"steamid": OTHER_ID}]}},
            {"response": {"players": [PLAYER, PLAYER]}},
            {"response": {"players": [PLAYER], "success": False}},
            {"response": {"players": [PLAYER], "error": "untrusted server text"}},
        ):
            with self.subTest(payload=payload), patch("requests.get", return_value=response(payload)):
                with self.assertRaises(SteamResponseError):
                    fetch_player_summary(KEY, STEAM_ID)
        with patch("requests.get", return_value=response({"response": {"players": []}})):
            with self.assertRaises(SteamAccountNotFound):
                fetch_player_summary(KEY, STEAM_ID)
        invalid_json = response()
        invalid_json._content = f"not json {KEY}".encode()
        with patch("requests.get", return_value=invalid_json):
            with self.assertRaises(SteamResponseError) as caught:
                fetch_player_summary(KEY, STEAM_ID)
            self.assertNotIn(KEY, str(caught.exception))


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    """Use native HA entries and update helpers, with all HTTP mocked."""

    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        self.get_patch = patch("requests.get", return_value=response({"response": {"players": [PLAYER]}}))
        self.get = self.get_patch.start()
        self.reload_patch = patch.object(self.hass.config_entries, "async_schedule_reload")
        self.reload = self.reload_patch.start()

    async def asyncTearDown(self):
        await self.hass.async_block_till_done()
        await self.hass.async_stop(force=True)
        self.reload_patch.stop()
        self.get_patch.stop()
        self.directory.cleanup()

    def entry(self, steam_id=STEAM_ID):
        entry = ConfigEntry(
            data={**DATA, "steam_id": steam_id}, domain=DOMAIN,
            discovery_keys={}, minor_version=1, options={"preserved": True},
            source="user", subentries_data=[], title="Account label",
            unique_id=steam_id, version=1,
        )
        self.hass.config_entries._entries[entry.entry_id] = entry
        return entry

    def flow(self, source="user", entry=None):
        flow = SteamTrackerConfigFlow()
        flow.hass = self.hass
        flow.handler = DOMAIN
        flow.context = {"source": source}
        if entry is not None:
            flow.context["entry_id"] = entry.entry_id
        return flow

    async def test_user_setup_checks_access_in_executor_and_trims_input(self):
        thread_ids = []

        def get(*args, **kwargs):
            thread_ids.append(threading.get_ident())
            return response({"response": {"players": [PLAYER]}})

        self.get.side_effect = get
        flow = self.flow()
        result = await flow.async_step_user({key: f" {value} " for key, value in DATA.items()})
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], DATA)
        self.assertEqual(result["title"], DATA["name"])
        self.assertEqual(flow.unique_id, STEAM_ID)
        self.assertNotEqual(thread_ids, [threading.get_ident()])
        self.assertEqual(len(thread_ids), 1)

    async def test_local_validation_and_duplicates_never_request_or_replace_keys(self):
        for field, value, error in (
            ("steam_id", "", "steam_id_required"),
            ("steam_id", "not-a-steam-id", "invalid_steam_id"),
            ("steam_id", "0" * 17, "invalid_steam_id"),
            ("steam_id", "１" * 17, "invalid_steam_id"),
            ("api_key", " ", "api_key_required"),
        ):
            with self.subTest(error=error, value=value):
                result = await self.flow().async_step_user({**DATA, field: value})
                self.assertEqual(result["errors"], {field: error})
        entry = self.entry()
        with self.assertRaises(AbortFlow) as caught:
            await self.flow().async_step_user({**DATA, "api_key": NEW_KEY, "name": "Changed"})
        self.assertEqual(caught.exception.reason, "already_configured")
        self.assertEqual(dict(entry.data), DATA)
        self.get.assert_not_called()
        self.reload.assert_not_called()

    async def test_setup_errors_are_specific_and_do_not_reflect_credentials(self):
        cases = (
            (response(status=403), {"api_key": "invalid_auth"}),
            (response(status=503), {"base": "cannot_connect"}),
            (requests.ReadTimeout(f"untrusted {KEY}"), {"base": "cannot_connect"}),
            (response({}), {"base": "invalid_response"}),
            (response({"response": {"players": []}}), {"steam_id": "account_not_found"}),
        )
        for reply, errors in cases:
            with self.subTest(errors=errors):
                self.get.side_effect = reply if isinstance(reply, Exception) else None
                self.get.return_value = reply
                result = await self.flow().async_step_user(DATA)
                self.assertEqual(result["type"], "form")
                self.assertEqual(result["errors"], errors)
                self.assertNotIn(KEY, repr(result))
                for field in result["data_schema"].schema:
                    if field.schema == "api_key":
                        self.assertNotIn("suggested_value", field.description or {})

    async def test_import_validates_before_creating(self):
        result = await self.flow("import").async_step_import(DATA)
        self.assertEqual(result["type"], "create_entry")
        self.get.return_value = response(status=401)
        result = await self.flow("import").async_step_import(DATA)
        self.assertEqual(result["reason"], "invalid_auth")
        self.get.reset_mock()
        result = await self.flow("import").async_step_import({"steam_id": STEAM_ID})
        self.assertEqual(result["reason"], "missing_import_data")
        self.get.assert_not_called()

    async def test_reconfigure_and_reauth_preserve_entry_and_other_accounts(self):
        entry = self.entry()
        other = self.entry(OTHER_ID)
        for source in ("reconfigure", "reauth"):
            with self.subTest(source=source):
                self.hass.config_entries.async_update_entry(entry, data=DATA)
                self.reload.reset_mock()
                flow = self.flow(source, entry)
                if source == "reauth":
                    result = await flow.async_step_reauth(dict(entry.data))
                    step = flow.async_step_reauth_confirm
                else:
                    result = await flow.async_step_reconfigure()
                    step = flow.async_step_reconfigure
                self.assertEqual(result["type"], "form")
                self.assertNotIn(KEY, repr(result))
                result = await step({"api_key": f" {NEW_KEY} "})
                self.assertEqual(result["reason"], f"{source}_successful")
                self.assertIs(self.hass.config_entries.async_get_entry(entry.entry_id), entry)
                self.assertEqual(dict(entry.data), {**DATA, "api_key": NEW_KEY})
                self.assertEqual(entry.unique_id, STEAM_ID)
                self.assertEqual(entry.title, "Account label")
                self.assertEqual(dict(entry.options), {"preserved": True})
                self.assertEqual(other.data["api_key"], KEY)
                self.reload.assert_called_once_with(entry.entry_id)

    async def test_failed_key_changes_leave_entry_untouched(self):
        entry = self.entry()
        for source in ("reconfigure", "reauth"):
            flow = self.flow(source, entry)
            step = flow.async_step_reconfigure if source == "reconfigure" else flow.async_step_reauth_confirm
            for reply, expected in (
                (response(status=403), {"api_key": "invalid_auth"}),
                (response(status=500), {"base": "cannot_connect"}),
                (response({"response": {"players": []}}), {"base": "account_not_found"}),
                (response({"response": {"players": [{"steamid": OTHER_ID}]}}), {"base": "invalid_response"}),
            ):
                with self.subTest(source=source, expected=expected):
                    self.get.return_value = reply
                    result = await step({"api_key": NEW_KEY})
                    self.assertEqual(result["errors"], expected)
                    self.assertEqual(dict(entry.data), DATA)
            self.get.reset_mock()
            result = await step({"api_key": " "})
            self.assertEqual(result["errors"], {"api_key": "api_key_required"})
            self.get.assert_not_called()
        self.reload.assert_not_called()

    async def test_key_validation_bypasses_cache_and_reloaded_sensors_start_fresh(self):
        entry = self.entry()
        original = []
        await async_setup_sensors(self.hass, entry, original.extend)
        await self.hass.async_add_executor_job(original[0].update)
        self.get.reset_mock()
        self.get.return_value = response(status=403)
        flow = self.flow("reconfigure", entry)
        result = await flow.async_step_reconfigure({"api_key": NEW_KEY})
        self.assertEqual(result["errors"], {"api_key": "invalid_auth"})
        self.assertEqual(entry.data["api_key"], KEY)
        self.get.assert_called_once()
        self.assertEqual(self.get.call_args.kwargs["headers"], {"x-webapi-key": NEW_KEY})
        self.get.return_value = response({"response": {"players": [PLAYER]}})
        result = await flow.async_step_reconfigure({"api_key": NEW_KEY})
        self.assertEqual(result["reason"], "reconfigure_successful")
        replacement = []
        await async_setup_sensors(self.hass, entry, replacement.extend)
        self.assertIsNot(original[0]._player_summary_cache, replacement[0]._player_summary_cache)
        self.assertEqual([sensor.unique_id for sensor in original], [sensor.unique_id for sensor in replacement])
        self.assertEqual(original[0].device_info, replacement[0].device_info)
        self.get.reset_mock()
        await self.hass.async_add_executor_job(replacement[0].update)
        await self.hass.async_add_executor_job(replacement[1].update)
        self.get.assert_called_once()
        self.assertEqual(self.get.call_args.kwargs["headers"], {"x-webapi-key": NEW_KEY})

    async def test_native_reauth_flow_is_deduplicated_and_completes(self):
        entry = self.entry()
        manager = self.hass.config_entries.flow

        async def create_flow(handler, *, context, data):
            flow = self.flow(context["source"], entry)
            flow.init_step = context["source"]
            return flow

        # Bypass integration discovery and the repair notification, while using
        # HA's native flow manager, locking, step dispatch, and entry updates.
        with (
            patch.object(manager, "async_create_flow", side_effect=create_flow),
            patch("homeassistant.config_entries.ir.async_create_issue"),
        ):
            entry.async_start_reauth(self.hass)
            entry.async_start_reauth(self.hass)
            await self.hass.async_block_till_done()
            active = manager.async_progress_by_handler(DOMAIN)
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["step_id"], "reauth_confirm")
            self.get.assert_not_called()
            self.get.return_value = response(status=403)
            result = await manager.async_configure(active[0]["flow_id"], {"api_key": NEW_KEY})
            self.assertEqual(result["errors"], {"api_key": "invalid_auth"})
            self.assertEqual(dict(entry.data), DATA)
            self.get.return_value = response({"response": {"players": [PLAYER]}})
            result = await manager.async_configure(active[0]["flow_id"], {"api_key": NEW_KEY})
            self.assertEqual(result["reason"], "reauth_successful")
            self.assertEqual(entry.data["api_key"], NEW_KEY)
            self.assertEqual(manager.async_progress_by_handler(DOMAIN), [])
            self.reload.assert_called_once_with(entry.entry_id)

    async def test_only_player_summary_denials_request_reauth_and_recover(self):
        entry = self.entry()
        for sensor_class in (SteamStatusSensor, SteamGameSensor):
            sensor = sensor_class(KEY, STEAM_ID, "Fictional sensor")
            sensor.hass = self.hass
            sensor.platform = SimpleNamespace(config_entry=entry)
            with patch.object(entry, "async_start_reauth") as reauth:
                for status in (401, 403, 429, 500):
                    with self.subTest(sensor=sensor_class, status=status):
                        reauth.reset_mock()
                        self.get.return_value = response(status=status)
                        await self.hass.async_add_executor_job(sensor.update)
                        await self.hass.async_block_till_done()
                        self.assertFalse(sensor.available)
                        self.assertIsNone(sensor.native_value)
                        self.assertEqual(sensor.extra_state_attributes, {})
                        if status in (401, 403):
                            reauth.assert_called_once_with(self.hass)
                        else:
                            reauth.assert_not_called()
                self.get.side_effect = requests.ReadTimeout(f"untrusted {KEY}")
                reauth.reset_mock()
                with self.assertLogs("custom_components.steam_tracker.sensor", level="ERROR") as logs:
                    await self.hass.async_add_executor_job(sensor.update)
                await self.hass.async_block_till_done()
                reauth.assert_not_called()
                self.assertNotIn(KEY, " ".join(logs.output))
                self.get.side_effect = None
                self.get.return_value = response({"response": {"players": [PLAYER]}})
                await self.hass.async_add_executor_job(sensor.update)
                self.assertTrue(sensor.available)
                reauth.assert_not_called()

    async def test_supplementary_failure_and_legacy_yaml_do_not_request_reauth(self):
        entry = self.entry()
        sensor = SteamGameSensor(KEY, STEAM_ID, "Fictional game")
        sensor.hass = self.hass
        sensor.platform = SimpleNamespace(config_entry=entry)
        self.get.side_effect = [
            response({"response": {"players": [{**PLAYER, "gameid": "1", "gameextrainfo": "Fictional Game"}]}}),
            response(status=403),
        ]
        with patch.object(entry, "async_start_reauth") as reauth:
            await self.hass.async_add_executor_job(sensor.update)
            await self.hass.async_block_till_done()
            self.assertTrue(sensor.available)
            self.assertEqual(sensor.native_value, "Fictional Game")
            reauth.assert_not_called()
            sensor.platform = SimpleNamespace(config_entry=None)
            self.get.side_effect = None
            self.get.return_value = response(status=403)
            await self.hass.async_add_executor_job(sensor.update)
            await self.hass.async_block_till_done()
            self.assertFalse(sensor.available)
            reauth.assert_not_called()


class ConfigurationTranslationTests(unittest.TestCase):
    def test_configuration_translations_match(self):
        root = Path(__file__).resolve().parents[1] / "custom_components/steam_tracker"
        source = json.loads((root / "strings.json").read_text(encoding="utf-8"))
        english = json.loads((root / "translations/en.json").read_text(encoding="utf-8"))
        german = json.loads((root / "translations/de.json").read_text(encoding="utf-8"))
        self.assertEqual(source, english)

        def leaves(value, prefix=()):
            result = {}
            for key, item in value.items():
                path = (*prefix, key)
                if isinstance(item, dict):
                    result.update(leaves(item, path))
                else:
                    result[path] = item
            return result

        source_strings, german_strings = leaves(source), leaves(german)
        self.assertEqual(source_strings.keys(), german_strings.keys())
        for path, text in source_strings.items():
            self.assertEqual("{name}" in text, "{name}" in german_strings[path])


if __name__ == "__main__":
    unittest.main()
