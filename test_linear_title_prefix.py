import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4861",
            "title": "Creating CRUD methods for PSQO service",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4861",
                "title": "Cursor researching: Creating CRUD methods for PSQO service",
            },
        )

    def test_accepts_cloud_automation_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to_research",
                "status": "To Research",
                "id": "POI-4861",
                "title": "Creating CRUD methods for PSQO service",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4861",
                "title": "Cursor researching: Creating CRUD methods for PSQO service",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4861",
            "title": "Creating CRUD methods for PSQO service",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4861",
                "title": "Creating CRUD methods for PSQO service",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_generic_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4861",
                    "title": "Creating CRUD methods for PSQO service",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4861",
                "title": "Cursor researching: Creating CRUD methods for PSQO service",
            },
        )

    def test_accepts_status_from_changes_new_value(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"old": "Todo", "new": "To Research"}},
            "data": {
                "identifier": "POI-4861",
                "title": "Creating CRUD methods for PSQO service",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4861",
                "title": "Cursor researching: Creating CRUD methods for PSQO service",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4861",
            "title": "cursor researching: Creating CRUD methods for PSQO service",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4861",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Creating CRUD methods for PSQO service",
                }
            )
        )

    def test_alias_matches_primary_entrypoint(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "id": "POI-4861",
            "title": "Creating CRUD methods for PSQO service",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4861",
            "title": "Creating CRUD methods for PSQO service",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4861",
                "title": "Cursor researching: Creating CRUD methods for PSQO service",
            },
        )


if __name__ == "__main__":
    unittest.main()
