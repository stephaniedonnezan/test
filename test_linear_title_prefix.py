import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "[Energy Allocation] GoO Cancelation Deletion",
                "id": "POI-4831",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4831",
                "title": "Cursor researching: [Energy Allocation] GoO Cancelation Deletion",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "title": "[Energy Allocation] GoO Cancelation Deletion",
                "id": "POI-4831",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Document database delete action",
                "id": "POI-4831",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "title": "cursor researching: Document database delete action",
                "id": "POI-4831",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_variants(self):
        for status_name in ("to research", "To-Research", "to_research", "toResearch"):
            with self.subTest(status_name=status_name):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status_name,
                        "title": "Document database delete action",
                        "id": "POI-4831",
                    },
                }

                update = build_issue_title_update(event)

                self.assertIsNotNone(update)
                self.assertEqual(update["title"], "Cursor researching: Document database delete action")

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4831",
                    "title": "Document database delete action",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4831",
                "title": "Cursor researching: Document database delete action",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4831",
                    "title": "Document database delete action",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event_without_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4831",
            },
        }
        event_without_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Document database delete action",
            },
        }

        self.assertIsNone(build_issue_title_update(event_without_title))
        self.assertIsNone(build_issue_title_update(event_without_id))

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Document database delete action",
                "id": "POI-4831",
            },
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
                "issueId": "POI-4831",
                "title": "Cursor researching: Document database delete action",
            },
        )

    def test_cli_exits_without_output_for_non_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "title": "Document database delete action",
                "id": "POI-4831",
            },
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
