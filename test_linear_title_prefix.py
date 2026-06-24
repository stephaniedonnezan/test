import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3551",
                "title": "Front end implementation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3551",
                "title": "Cursor researching: Front end implementation",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3551",
                "title": "Front end implementation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3551",
                "title": "Front end implementation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "ToResearch",
                "issueId": "POI-3551",
                "title": "Front end implementation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Front end implementation",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3551",
                "title": "cursor researching: Front end implementation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Front end implementation",
        )

    def test_nested_linear_update_uses_current_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-3551",
                "title": "Front end implementation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3551",
                "title": "Cursor researching: Front end implementation",
            },
        )

    def test_nested_linear_update_prefers_issue_id_over_webhook_id(self):
        event = {
            "id": "webhook-delivery-id",
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Front end implementation",
                    "status": {"name": "to research"},
                }
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "linear-issue-id")

    def test_reads_new_status_from_change_details(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "to-research"}},
            "issueId": "POI-3551",
            "title": "Front end implementation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Front end implementation",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_json_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3551",
            "title": "Front end implementation",
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
                "issueId": "POI-3551",
                "title": "Cursor researching: Front end implementation",
            },
        )


if __name__ == "__main__":
    unittest.main()
