import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4806",
            "title": "QA report",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4806",
                "title": "Cursor researching: QA report",
            },
        )

    def test_accepts_automation_trigger_context_shape(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-123",
                "title": "Implement title prefix",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Implement title prefix",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Backlog",
            "id": "POI-4806",
            "title": "QA report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_events_that_are_not_status_changes(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4806",
            "title": "QA report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4806",
            "title": "cursor researching: QA report",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4806",
            "title": "QA report",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: QA report",
        )

    def test_accepts_linear_issue_update_when_state_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-4806",
                "title": "QA report",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: QA report",
            },
        )

    def test_accepts_updated_from_state_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "identifier": "POI-4806",
                "title": "QA report",
                "workflowState": {"name": "TO-RESEARCH"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4806",
                "title": "Cursor researching: QA report",
            },
        )

    def test_ignores_linear_update_when_changed_field_is_not_status(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4806",
                "title": "QA report",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "QA report",
        }
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4806",
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "issueId": "  POI-4806  ",
            "title": "  QA report  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4806",
                "title": "Cursor researching: QA report",
            },
        )

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4806",
            "title": "QA report",
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
                "issueId": "POI-4806",
                "title": "Cursor researching: QA report",
            },
        )


if __name__ == "__main__":
    unittest.main()
