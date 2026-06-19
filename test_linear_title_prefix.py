import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self) -> None:
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Add database checks on transport-segment entity",
                "id": "POI-4758",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4758",
                "title": "Cursor researching: Add database checks on transport-segment entity",
            },
        )

    def test_status_match_is_case_separator_and_whitespace_insensitive(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "  To-Research ",
                "title": "Issue title",
                "id": "POI-1234",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_builds_update_for_linear_issue_update_payload(self) -> None:
        event = {
            "webhookType": "Issue",
            "action": "update",
            "updatedFrom": {"stateId": "previous-state-id"},
            "data": {
                "identifier": "POI-9876",
                "title": "Research calculation assumptions",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9876",
                "title": "Cursor researching: Research calculation assumptions",
            },
        )

    def test_supports_changes_payload_with_new_status(self) -> None:
        event = {
            "action": "updated",
            "changes": [
                {
                    "field": "status",
                    "newValue": {"name": "to_research"},
                }
            ],
            "issue": {
                "identifier": "POI-4321",
                "title": "Investigate emission factors",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4321",
                "title": "Cursor researching: Investigate emission factors",
            },
        )

    def test_returns_none_for_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "title": "Issue title",
                "id": "POI-1234",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_change_events(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
                "id": "POI-1234",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        prefixed_titles = (
            "Cursor researching: Issue title",
            "cursor researching - Issue title",
            " Cursor researching Issue title",
        )

        for title in prefixed_titles:
            with self.subTest(title=title):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": title,
                        "id": "POI-1234",
                    },
                }

                self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_required_issue_data_is_missing(self) -> None:
        self.assertIsNone(build_issue_title_update({"triggerContext": "bad"}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                    }
                }
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_reads_event_file_and_prints_action(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
                "id": "POI-1234",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            event_path = Path(temp_dir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(event_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Issue title",
            },
        )


if __name__ == "__main__":
    unittest.main()
