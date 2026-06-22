import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_payload(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5073",
                "title": "Backend e2e to test scenarios is escapable by user",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5073",
                "title": "Cursor researching: Backend e2e to test scenarios is escapable by user",
            },
        )

    def test_normalizes_status_and_trigger_variants(self) -> None:
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate importer",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate importer",
            },
        )

    def test_uses_nested_linear_issue_payload(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-2",
                "title": "Compare reported values",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Compare reported values",
            },
        )

    def test_ignores_non_status_change_trigger(self) -> None:
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-3",
            "title": "Review report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "issueId": "POI-4",
            "title": "Review report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-5",
            "title": "cursor researching: Review report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-6",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Untethered title",
                }
            )
        )

    def test_cli_prints_update_action(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "issueId": "POI-7",
            "title": "Run export checks",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Run export checks",
            },
        )


if __name__ == "__main__":
    unittest.main()
