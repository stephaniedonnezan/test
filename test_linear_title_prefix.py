import json
import subprocess
import sys
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_gets_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
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

    def test_nested_automation_trigger_context_payload_gets_prefixed(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5065",
                "title": "UBA POS should not be modifiable",
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

    def test_wrapped_automation_trigger_info_payload_gets_prefixed(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-5065",
                    "title": " UBA POS should not be modifiable ",
                },
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

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_with_status_field_change_gets_prefixed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "To Research"},
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

    def test_changes_payload_can_provide_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"old": "Backlog", "new": "To Research"}},
            "issue": {
                "id": "POI-5065",
                "title": "UBA POS should not be modifiable",
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

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "cursor researching: UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }
        script = Path(__file__).with_name("linear_title_prefix.py")

        completed = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )


if __name__ == "__main__":
    unittest.main()
