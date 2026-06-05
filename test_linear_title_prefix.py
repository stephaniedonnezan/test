import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_payload_gets_prefixed_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Empty link dialog if no possible allocations",
            },
        )

    def test_status_changed_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4820",
            "title": "Research handoff",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Research handoff",
            },
        )

    def test_nested_linear_update_uses_updated_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4820",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_change_payload_prefers_new_status_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "data": {
                "issue": {
                    "id": "POI-4820",
                    "title": "Changed workflow state",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Changed workflow state",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4820",
            "title": "Working issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4820",
            "title": "Renamed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4820",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4820",
                    "title": " ",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Untitled issue",
                }
            )
        )

    def test_cli_outputs_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Empty link dialog if no possible allocations",
            },
        )


if __name__ == "__main__":
    unittest.main()
