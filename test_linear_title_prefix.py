import json
import subprocess
import sys
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4083",
                "title": "Container Wrappers",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4083",
                "title": "Cursor researching: Container Wrappers",
            },
        )

    def test_prefixes_automation_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4083",
                    "title": "Container Wrappers",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4083")
        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_prefixes_nested_automation_trigger_info_payload(self):
        update = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "trigger": "statusChanged",
                        "newStatus": "toResearch",
                        "id": "POI-4083",
                        "title": "Container Wrappers",
                    }
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_prefixes_linear_issue_update_when_status_field_changed(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-4083",
                    "title": "Container Wrappers",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4083")
        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_prefixes_linear_changes_payload(self):
        update = build_issue_title_update(
            {
                "action": "Issue Updated",
                "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
                "data": {
                    "identifier": "POI-4083",
                    "title": "Container Wrappers",
                },
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_normalizes_status_separators(self):
        update = build_issue_title_update(
            {
                "trigger": "status-changed",
                "new_status": "to_research",
                "issueId": "POI-4083",
                "title": "Container Wrappers",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_ignores_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4083",
                "title": "Container Wrappers",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_triggers(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4083",
                "title": "Container Wrappers",
            }
        )

        self.assertIsNone(update)

    def test_ignores_generic_issue_update_without_status_change(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "status": "to research",
                "id": "POI-4083",
                "title": "Container Wrappers",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4083",
                "title": "Cursor researching: Container Wrappers",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4083",
                "title": "cursor researching - Container Wrappers",
            }
        )

        self.assertIsNone(update)

    def test_trims_issue_id_and_title(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": " POI-4083 ",
                "title": " Container Wrappers ",
            }
        )

        self.assertEqual(update["issueId"], "POI-4083")
        self.assertEqual(update["title"], "Cursor researching: Container Wrappers")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4083",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Container Wrappers",
                }
            )
        )

    def test_cli_prints_update_action(self):
        script = Path(__file__).with_name("linear_title_prefix.py")
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4083",
            "title": "Container Wrappers",
        }

        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4083",
                "title": "Cursor researching: Container Wrappers",
            },
        )


if __name__ == "__main__":
    unittest.main()
