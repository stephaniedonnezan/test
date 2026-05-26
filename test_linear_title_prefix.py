import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_payload_when_status_changes_to_research(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3293",
                    "title": "[TBSpecified]Versioning of the POS",
                }
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-3293",
                "title": "Cursor researching: [TBSpecified]Versioning of the POS",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Canceled",
                    "id": "POI-3293",
                    "title": "[TBSpecified]Versioning of the POS",
                }
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_change_events(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-3293",
                    "title": "[TBSpecified]Versioning of the POS",
                }
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_existing_prefix(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3293",
                    "title": "cursor researching: [TBSpecified]Versioning of the POS",
                }
            }
        )

        self.assertIsNone(action)

    def test_normalizes_status_name_variants(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "new_status": "to_research",
                    "identifier": "POI-3293",
                    "issueTitle": "Versioning of the POS",
                }
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Versioning of the POS")

    def test_supports_nested_linear_issue_payloads(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-3293",
                        "title": "Versioning of the POS",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-3293",
                "title": "Cursor researching: Versioning of the POS",
            },
        )

    def test_prefers_new_status_over_stale_issue_status(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Canceled",
                    "issue": {
                        "id": "POI-3293",
                        "title": "Versioning of the POS",
                        "status": "To Research",
                    },
                }
            }
        )

        self.assertIsNone(action)

    def test_supports_updated_fields_with_new_status_value(self):
        action = build_issue_title_update(
            {
                "type": "Issue updated",
                "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
                "data": {
                    "id": "issue-id",
                    "identifier": "POI-3293",
                    "title": "Versioning of the POS",
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-3293")
        self.assertEqual(action["title"], "Cursor researching: Versioning of the POS")

    def test_cli_prints_action_as_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3293",
                "title": "Versioning of the POS",
            }
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
                "issueId": "POI-3293",
                "title": "Cursor researching: Versioning of the POS",
            },
        )


if __name__ == "__main__":
    unittest.main()
