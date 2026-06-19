import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_for_flat_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4004",
            "title": "Make mass balance shape correct",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4004",
                "title": "Cursor researching: Make mass balance shape correct",
            },
        )

    def test_accepts_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4004",
                    "title": "Container sites shape",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4004")
        self.assertEqual(update["title"], "Cursor researching: Container sites shape")

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4004",
                    "title": "Nested Linear issue",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4004",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "To-Research"}}},
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Changed workflow status",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Changed workflow status",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4004",
            "title": "Already in QA",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4004",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4004",
            "title": "Description changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4004",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4004",
                    "title": " ",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4004",
            "title": "CLI issue",
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
                "issueId": "POI-4004",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
