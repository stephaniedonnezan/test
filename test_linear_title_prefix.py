import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_automation_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )

    def test_accepts_status_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "Build exports",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Build exports",
            },
        )

    def test_nested_linear_update_uses_changed_status_destination(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Reconcile transfers",
                    "state": {"name": "In Review"},
                }
            },
            "updatedFields": ["state"],
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Reconcile transfers",
            },
        )

    def test_changes_list_payload(self):
        event = {
            "webhookType": "Issue Updated",
            "data": {
                "issue": {
                    "key": "POI-789",
                    "title": "Review settlements",
                }
            },
            "changes": [
                {"field": "workflowState", "new": {"name": "To Research"}},
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review settlements",
            },
        )

    def test_skips_non_status_update_event(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-123",
            "title": "Build exports",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-123",
            "title": "Build exports",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Build exports",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "cursor researching: Build exports",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "cursor researching: Build exports",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_matching_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
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
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
