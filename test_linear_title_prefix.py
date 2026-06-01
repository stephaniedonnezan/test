import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4458",
                "title": "Create endpoint to lock a production site's outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4458",
                "title": "Cursor researching: Create endpoint to lock a production site's outputs",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4458",
                "title": "Create endpoint to lock a production site's outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4458",
                "title": "Create endpoint to lock a production site's outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4458",
                "title": "cursor researching: Create endpoint",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_trigger_and_hyphenated_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "issueId": "POI-4458",
                "title": " Create endpoint ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4458",
                "title": "Cursor researching: Create endpoint",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "issue-id-1",
                "title": "Create endpoint",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id-1",
                "title": "Cursor researching: Create endpoint",
            },
        )

    def test_ignores_old_status_values_from_updated_from(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "issue-id-1",
                "title": "Create endpoint",
                "state": {"name": "In Review"},
            },
            "updatedFrom": {"state": {"name": "To Research"}},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "issue-id-1",
                "title": "Create endpoint",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"title": "Old title"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_issue_when_data_wraps_issue(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "identifier": "POI-4458",
                    "title": "Create endpoint",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4458",
                "title": "Cursor researching: Create endpoint",
            },
        )

    def test_cli_outputs_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4458",
                "title": "Create endpoint",
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
                "issueId": "POI-4458",
                "title": "Cursor researching: Create endpoint",
            },
        )


if __name__ == "__main__":
    unittest.main()
