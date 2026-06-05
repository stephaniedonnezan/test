import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


ISSUE_TITLE = 'Redesign of "Add Input"'


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_current_automation_payload_prefixes_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": ISSUE_TITLE,
                "id": "POI-4838",
                "url": "https://linear.app/atmen/issue/POI-4838/redesign-of-add-input",
                "status": "To Research",
                "statusType": "unstarted",
                "priority": "Medium",
                "assignee": "Philipp Haase",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "issueId": "POI-4838",
            "title": ISSUE_TITLE,
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_accepts_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4838",
                    "title": ISSUE_TITLE,
                    "workflowState": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4838",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4838",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4838",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4838",
            "title": f"cursor researching: {ISSUE_TITLE}",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4838",
            "title": " ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4838",
                "title": ISSUE_TITLE,
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )


if __name__ == "__main__":
    unittest.main()
