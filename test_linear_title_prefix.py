import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "Supply contract title copy is confusing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract title copy is confusing",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "Supply contract title copy is confusing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-5045",
                "title": "Supply contract title copy is confusing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-5045",
                "title": "Supply contract title copy is confusing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract title copy is confusing",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "cursor researching: Supply contract title copy is confusing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract title copy is confusing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract title copy is confusing",
            },
        )

    def test_ignores_generic_updates_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract title copy is confusing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_changes_to_value(self):
        event = {
            "webhookType": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "to research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract title copy is confusing",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract title copy is confusing",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "Supply contract title copy is confusing",
            }
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
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract title copy is confusing",
            },
        )


if __name__ == "__main__":
    unittest.main()
