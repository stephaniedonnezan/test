import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_cursor_status_change_to_research_issue(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5065",
                "title": "UBA POS should not be modifiable",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_accepts_flat_cursor_payload(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "cursor researching: UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_accepts_status_from_linear_changes_payload(self):
        event = {
            "webhookType": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                }
            },
            "changes": {
                "workflowState": {
                    "old": {"name": "Todo"},
                    "new": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5065",
                }
            )
        )

    def test_cli_outputs_update_action_for_valid_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
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
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )


if __name__ == "__main__":
    unittest.main()
