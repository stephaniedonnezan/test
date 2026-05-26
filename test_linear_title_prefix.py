import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_automation_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4660",
                "title": "Site switch on the site name",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4660",
            "title": "Site switch on the site name",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4660",
            "title": "Site switch on the site name",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4660",
            "title": "cursor researching: Site switch on the site name",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separator_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4660",
            "title": "Site switch on the site name",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Site switch on the site name",
        )

    def test_accepts_linear_update_payload_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4660",
                "title": "Site switch on the site name",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_accepts_changed_fields_and_new_state_payload(self):
        event = {
            "action": "Issue Updated",
            "changedFields": {"workflowState": {"old": "Todo"}},
            "newWorkflowState": "toResearch",
            "data": {
                "issue": {
                    "id": "POI-4660",
                    "title": "Site switch on the site name",
                }
            },
        }

        self.assertEqual(
            handle_issue_status_changed(event)["title"],
            "Cursor researching: Site switch on the site name",
        )

    def test_accepts_state_changed_trigger(self):
        event = {
            "trigger": "state_changed",
            "state": {"name": "to research"},
            "identifier": "POI-4660",
            "title": "Site switch on the site name",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4660",
        )

    def test_ignores_linear_update_payload_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4660",
                "title": "Site switch on the site name",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4660",
            "title": "Site switch on the site name",
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
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )


if __name__ == "__main__":
    unittest.main()
