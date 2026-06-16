import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )

    def test_prefixes_title_for_cursor_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4933",
                "title": "Add a meter as example",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )

    def test_accepts_status_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add a meter as example",
        )

    def test_uses_nested_linear_issue_data(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-value",
                    "identifier": "POI-4933",
                    "title": "Add a meter as example",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )

    def test_reads_new_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "To Research"}}},
            "identifier": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add a meter as example",
        )

    def test_reads_new_status_from_changes_sequence(self):
        event = {
            "type": "Updated Issue",
            "changes": [
                {
                    "fieldName": "status",
                    "after": "to_research",
                }
            ],
            "identifier": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add a meter as example",
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4933",
            "title": "Add a meter as example",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4933",
            "title": "cursor researching: Add a meter as example",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Add a meter as example",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4933",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Add a meter as example",
                }
            )
        )

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4933",
            "title": "Add a meter as example",
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
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )


if __name__ == "__main__":
    unittest.main()
