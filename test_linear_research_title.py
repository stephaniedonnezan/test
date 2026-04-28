import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_research_title import RESEARCHING_PREFIX
from linear_research_title import updated_title_for_status_change
from linear_research_title import with_researching_prefix


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix_to_title(self) -> None:
        self.assertEqual(
            with_researching_prefix("Delivery 7846 certificate number mismatch"),
            "Cursor researching - Delivery 7846 certificate number mismatch",
        )

    def test_keeps_existing_hyphen_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Delivery 7846"),
            "Cursor researching - Delivery 7846",
        )

    def test_keeps_existing_colon_prefix_case_insensitively(self) -> None:
        self.assertEqual(
            with_researching_prefix("cursor researching: Delivery 7846"),
            "cursor researching: Delivery 7846",
        )

    def test_blank_title_becomes_prefix(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCHING_PREFIX)


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_nested_linear_payload_when_status_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Delivery 7846 certificate number mismatch",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Delivery 7846 certificate number mismatch",
        )

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status changed",
                "newStatus": "  To   Research ",
                "title": "Delivery 7846",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Delivery 7846",
        )

    def test_supports_status_fallback_field(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "title": "Delivery 7846",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Delivery 7846",
        )

    def test_supports_raw_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Delivery 7846",
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Delivery 7846",
        )

    def test_ignores_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Delivery 7846",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_non_status_change_triggers(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Delivery 7846",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_already_prefixed_title(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Delivery 7846",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_invalid_payloads(self) -> None:
        self.assertIsNone(updated_title_for_status_change({"triggerContext": {}}))
        self.assertIsNone(updated_title_for_status_change({"triggerContext": "bad"}))


class CliTests(unittest.TestCase):
    def test_cli_prints_updated_title_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Delivery 7846",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "payload.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_research_title.py", "--input", str(input_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - Delivery 7846"},
        )


if __name__ == "__main__":
    unittest.main()
