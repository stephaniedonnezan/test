import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import prefix_researching_title


class PrefixResearchingTitleTests(unittest.TestCase):
    def test_prefixes_plain_title(self) -> None:
        self.assertEqual(
            prefix_researching_title("Revisit UX of Delivery Linking Dialog"),
            "Cursor researching: Revisit UX of Delivery Linking Dialog",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        self.assertEqual(
            prefix_researching_title(
                "cursor researching - Revisit UX of Delivery Linking Dialog"
            ),
            "cursor researching - Revisit UX of Delivery Linking Dialog",
        )

    def test_handles_blank_title(self) -> None:
        self.assertEqual(prefix_researching_title("   "), "Cursor researching")


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_updates_automation_trigger_context_for_to_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4266",
                "title": "Revisit UX of Delivery Linking Dialog",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4266",
                "title": "Cursor researching: Revisit UX of Delivery Linking Dialog",
            },
        )

    def test_status_match_accepts_case_and_separator_variants(self) -> None:
        payload = {
            "trigger": "statusChanged",
            "newStatus": "To_Research",
            "issueId": "POI-4266",
            "title": "Revisit UX of Delivery Linking Dialog",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4266",
                "title": "Cursor researching: Revisit UX of Delivery Linking Dialog",
            },
        )

    def test_ignores_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4266",
                "title": "Revisit UX of Delivery Linking Dialog",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_change_triggers(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "id": "POI-4266",
                "title": "Revisit UX of Delivery Linking Dialog",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_already_prefixed_title(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4266",
            "title": "Cursor researching: Revisit UX of Delivery Linking Dialog",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_accepts_nested_linear_issue_update_payload(self) -> None:
        payload = {
            "action": "update",
            "webhookType": "issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4266",
                    "title": "Revisit UX of Delivery Linking Dialog",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4266",
                "title": "Cursor researching: Revisit UX of Delivery Linking Dialog",
            },
        )

    def test_requires_issue_id_and_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4266",
                }
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_reads_payload_file_and_prints_update_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4266",
                "title": "Revisit UX of Delivery Linking Dialog",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

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
                "issueId": "POI-4266",
                "title": "Cursor researching: Revisit UX of Delivery Linking Dialog",
            },
        )


if __name__ == "__main__":
    unittest.main()
