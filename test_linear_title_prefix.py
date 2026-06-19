import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import (
    CURSOR_RESEARCHING_PREFIX,
    build_issue_title_update,
    derive_updated_title,
    update_issue_title_for_status,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_nested_status_changed_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4553",
                "title": "Add API to update document extractions results",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4553",
                "title": "Cursor researching: Add API to update document extractions results",
            },
        )

    def test_supports_flat_payload_shape_and_issue_id_field(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Investigate connection issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate connection issue",
            },
        )

    def test_supports_status_fallback_and_camel_case_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to research",
                "id": "POI-2",
                "title": "Research me",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research me",
        )

    def test_supports_nested_issue_identifier(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "issue": {"identifier": "POI-3"},
                "title": "Research me",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-3")

    def test_returns_none_for_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_status_other_than_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-5",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_prefixed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "cursor researching: Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
                "title": "  Research me  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Research me",
        )

    def test_returns_none_without_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not an event"))


class UpdatedTitleHelpersTest(unittest.TestCase):
    def test_derive_updated_title_does_not_require_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research me",
            }
        }

        self.assertEqual(derive_updated_title(event), "Cursor researching: Research me")

    def test_update_issue_title_for_status_prefixes_only_research_status(self):
        self.assertEqual(
            update_issue_title_for_status("Research me", "to research"),
            "Cursor researching: Research me",
        )
        self.assertEqual(
            update_issue_title_for_status("Research me", "in progress"),
            "Research me",
        )

    def test_update_issue_title_for_status_avoids_prefix_variants(self):
        self.assertEqual(
            update_issue_title_for_status("Cursor researching - Research me", "to research"),
            "Cursor researching - Research me",
        )


class CliTest(unittest.TestCase):
    def test_cli_outputs_title_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "Research me",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(event), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Research me",
            },
        )


if __name__ == "__main__":
    unittest.main()
