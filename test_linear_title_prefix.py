import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_to_research_issue(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3952",
                "title": "Turn2X cannot see their co2 qualified inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3952",
                "title": "Cursor researching: Turn2X cannot see their co2 qualified inputs",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-3952",
                "title": "Turn2X cannot see their co2 qualified inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3952",
                "title": "Turn2X cannot see their co2 qualified inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-3952",
                "title": "cursor researching: Turn2X cannot see their co2 qualified inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_to_research_status_separators_and_camel_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-3952",
                "title": "Turn2X cannot see their co2 qualified inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Turn2X cannot see their co2 qualified inputs",
        )

    def test_accepts_nested_linear_status_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3952",
                    "title": "Turn2X cannot see their co2 qualified inputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3952",
                "title": "Cursor researching: Turn2X cannot see their co2 qualified inputs",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-3952",
                    "title": "Turn2X cannot see their co2 qualified inputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_field_from_changes_for_generic_update(self):
        event = {
            "webhookType": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "id": "POI-3952",
            "title": "Turn2X cannot see their co2 qualified inputs",
            "workflowState": {"name": "To Research"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Turn2X cannot see their co2 qualified inputs",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3952",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Turn2X cannot see their co2 qualified inputs",
                }
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3952",
                "title": "Turn2X cannot see their co2 qualified inputs",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3952",
                "title": "Cursor researching: Turn2X cannot see their co2 qualified inputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
