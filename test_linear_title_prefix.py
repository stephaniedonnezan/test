import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4877",
                "title": "Rounding error in power allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4877",
            "title": "Rounding error in power allocation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Rounding error in power allocation",
        )

    def test_accepts_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4877",
                    "title": "Rounding error in power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_accepts_changes_object_for_status_updates(self):
        event = {
            "action": "updated",
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4877",
                    "title": "Rounding error in power allocation",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Rounding error in power allocation",
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4877",
                "title": "Rounding error in power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4877",
            "title": "Rounding error in power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4877",
                    "title": "Rounding error in power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4877",
            "title": "cursor researching: Rounding error in power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4877"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4877",
            "title": "Rounding error in power allocation",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
