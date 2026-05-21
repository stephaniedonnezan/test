import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_status_changed_to_research_prefixes_title(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4138",
                "title": "Really slow request",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4138",
                "title": "Cursor researching: Really slow request",
            },
        )

    def test_status_changed_to_non_research_status_is_ignored(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Triage",
                "id": "POI-4138",
                "title": "Really slow request",
            }
        )

        self.assertIsNone(update)

    def test_non_status_change_event_is_ignored(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4138",
                "title": "Really slow request",
            }
        )

        self.assertIsNone(update)

    def test_existing_title_marker_is_not_duplicated(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4138",
                "title": "cursor researching: Really slow request",
            }
        )

        self.assertIsNone(update)

    def test_supports_nested_automation_trigger_context(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to-research",
                    "id": "POI-4138",
                    "title": "Really slow request",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4138")
        self.assertEqual(update["title"], "Cursor researching: Really slow request")

    def test_supports_linear_issue_updated_payloads_with_state_name(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-4138",
                    "title": "Really slow request",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4138")
        self.assertEqual(update["title"], "Cursor researching: Really slow request")

    def test_issue_updated_without_status_field_is_ignored(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["assignee"],
                "data": {
                    "identifier": "POI-4138",
                    "title": "Really slow request",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(update)

    def test_missing_issue_identity_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Really slow request",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4138",
                }
            )
        )

    def test_cli_prints_update_action(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4138",
                    "title": "Really slow request",
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4138",
                "title": "Cursor researching: Really slow request",
            },
        )


if __name__ == "__main__":
    unittest.main()
