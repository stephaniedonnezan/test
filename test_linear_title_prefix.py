import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Custom LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-123",
            "title": "Custom LHV",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Custom LHV",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "cursor researching: Custom LHV",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "  Custom LHV  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "id": "lin_123",
                "identifier": "POI-123",
                "title": "Custom LHV",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin_123",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_ignores_issue_updates_without_status_change_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-123",
                "title": "Custom LHV",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-123"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Custom LHV"})
        )

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Custom LHV",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Custom LHV",
            },
        )


if __name__ == "__main__":
    unittest.main()
