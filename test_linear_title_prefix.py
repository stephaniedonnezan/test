import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_status_change_to_research_returns_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4545",
                "title": "[Container Logic MB] Deliveries connected to batches outside of site",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": (
                    "Cursor researching: "
                    "[Container Logic MB] Deliveries connected to batches outside of site"
                ),
            },
        )

    def test_done_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4545",
                "title": "[Container Logic MB] Deliveries connected to batches outside of site",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4545",
                "title": "Delivery card item",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4545",
                "title": "Delivery card item",
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4545")
        self.assertEqual(result["title"], "Cursor researching: Delivery card item")

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4545",
                "title": "cursor researching: Delivery card item",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "cursor researching: Delivery card item",
            },
        )

    def test_nested_linear_update_uses_nested_issue_identity(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-4545",
                    "title": "Delivery connection dialog",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery connection dialog",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4545",
                "title": "Delivery card item",
            }
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
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery card item",
            },
        )


if __name__ == "__main__":
    unittest.main()
