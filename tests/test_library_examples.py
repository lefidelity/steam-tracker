"""Render both languages' library examples with new, old and unavailable data."""

from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]


def library_templates():
    """Read the actual YAML shipped in the card guides and full dashboards."""
    for language in ("de", "en"):
        guide = ROOT / f"docs/examples/cards/README_{language}.md"
        section = guide.read_text(encoding="utf-8").split("### Library Statistics", 1)[1]
        snippet = section.split("```yaml\n", 1)[1].split("\n```", 1)[0]
        yield guide.name, yaml.safe_load(snippet)["content"]

        dashboard = ROOT / f"docs/examples/extended dashboard/steam_dashboard_{language}.yaml"
        content = yaml.safe_load(dashboard.read_text(encoding="utf-8"))

        def find_library(node):
            if isinstance(node, dict):
                text = node.get("content")
                if isinstance(text, str) and "'played_percentage'" in text:
                    yield text
                for child in node.values():
                    yield from find_library(child)
            elif isinstance(node, list):
                for child in node:
                    yield from find_library(child)

        templates = list(find_library(content))
        if len(templates) != 1:
            raise AssertionError(f"Expected one library card in {dashboard.name}")
        yield dashboard.name, templates[0]


class LibraryExampleTests(unittest.TestCase):
    def render(self, template, attributes, *, available=True):
        def state_attr(entity, key):
            self.assertEqual(entity, "sensor.steam_tracker_playtime")
            return attributes.get(key)

        return Environment(undefined=StrictUndefined).from_string(template).render(
            has_value=lambda entity: available, state_attr=state_attr
        )

    def test_new_statistics_and_five_distribution_bars(self):
        attrs = {
            "game_count": 8, "total_playtime_hours": 122,
            "top_5_playtime_hours": 121, "pile_of_shame_count": 3,
            "played_percentage": 87.5, "unplayed_game_count": 1,
            "top_5_playtime_percentage": 99.2,
            "playtime_distribution": {
                "unplayed": 1, "under_1_hour": 2, "1_to_10_hours": 2,
                "10_to_50_hours": 2, "50_hours_or_more": 1,
            },
        }
        templates = list(library_templates())
        self.assertEqual(len(templates), 4)
        for name, template in templates:
            with self.subTest(example=name):
                rendered = self.render(template, attrs)
                self.assertIn("87.5 %", rendered)
                self.assertIn("99.2 %", rendered)
                self.assertEqual(rendered.count("<code>"), 5)
                self.assertIn("≥50 h", rendered)

    def test_empty_library_renders_zero_values_without_division_by_zero(self):
        attrs = {
            "game_count": 0, "played_percentage": 0, "unplayed_game_count": 0,
            "top_5_playtime_percentage": 0,
            "playtime_distribution": dict.fromkeys(
                ("unplayed", "under_1_hour", "1_to_10_hours",
                 "10_to_50_hours", "50_hours_or_more"), 0
            ),
        }
        for name, template in library_templates():
            with self.subTest(example=name):
                rendered = self.render(template, attrs)
                self.assertEqual(rendered.count("<code>"), 5)
                self.assertIn("░" * 12, rendered)
                self.assertIn("0 %", rendered)

    def test_older_sensor_attributes_hide_new_statistics(self):
        for name, template in library_templates():
            with self.subTest(example=name):
                rendered = self.render(template, {"game_count": 1})
                self.assertNotIn("<code>", rendered)
                self.assertNotIn("Spielquote", rendered)
                self.assertNotIn("Played library", rendered)

    def test_unavailable_sensor_hides_statistics(self):
        for name, template in library_templates():
            with self.subTest(example=name):
                rendered = self.render(template, {}, available=False)
                self.assertNotIn("<table>", rendered)
                self.assertNotIn("<code>", rendered)


if __name__ == "__main__":
    unittest.main()
