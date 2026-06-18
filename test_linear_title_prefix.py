import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5071",
                "title": "User Manual lives in the repo",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5071",
                "title": "Cursor researching: User Manual lives in the repo",
            },
        )

    def test_accepts_status_changed_camel_case_and_status_casing(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-100",
            "title": "Investigate exposure report",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Investigate exposure report",
            },
        )

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "identifier": "POI-101",
                    "title": "Review importer behavior",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Review importer behavior",
            },
        )

    def test_accepts_new_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to_research"}}},
            "identifier": "POI-102",
            "title": "Research current permissions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-102",
                "title": "Cursor researching: Research current permissions",
            },
        )

    def test_accepts_new_status_from_changes_list(self):
        event = {
            "action": "updated",
            "changes": [{"field": "status", "to": "toResearch"}],
            "key": "POI-103",
            "title": "Confirm allocation rules",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-103",
                "title": "Cursor researching: Confirm allocation rules",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Triage",
            "id": "POI-104",
            "title": "Leave this title alone",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-105",
            "title": "Title-only edit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-106",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-107",
            "title": "CLI input",
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
                "issueId": "POI-107",
                "title": "Cursor researching: CLI input",
            },
        )


if __name__ == "__main__":
    unittest.main()
