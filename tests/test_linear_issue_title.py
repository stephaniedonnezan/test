import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_issue_title import (
    RESEARCHING_PREFIX,
    updated_title_for_status_change,
    with_researching_prefix,
)


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Redesign of Add Input"),
            f"{RESEARCHING_PREFIX} - Redesign of Add Input",
        )

    def test_does_not_duplicate_existing_hyphen_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Redesign of Add Input"),
            "Cursor researching - Redesign of Add Input",
        )

    def test_does_not_duplicate_existing_colon_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("cursor researching: Redesign of Add Input"),
            "cursor researching: Redesign of Add Input",
        )

    def test_handles_blank_title(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCHING_PREFIX)


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_wrapped_status_changed_payload_on_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Redesign of Add Input",
        )

    def test_updates_raw_status_changed_payload_on_normalized_status(self) -> None:
        payload = {
            "trigger": "Status Changed",
            "newStatus": "  To   Research ",
            "title": "Redesign of Add Input",
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Redesign of Add Input",
        )

    def test_supports_status_fallback_field(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Redesign of Add Input",
        )

    def test_ignores_non_to_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "title": "Redesign of Add Input",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_non_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Redesign of Add Input",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_already_prefixed_title(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Redesign of Add Input",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_missing_or_invalid_payload_data(self) -> None:
        self.assertIsNone(updated_title_for_status_change({"triggerContext": "bad"}))
        self.assertIsNone(updated_title_for_status_change({"triggerContext": {}}))
        self.assertIsNone(
            updated_title_for_status_change(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                    }
                }
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_outputs_updated_title_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Redesign of Add Input",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "linear_issue_title.py",
                    "--input",
                    str(payload_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - Redesign of Add Input"},
        )


if __name__ == "__main__":
    unittest.main()
