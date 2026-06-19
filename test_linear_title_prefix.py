import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4598",
                "title": "Make every mb use the same component",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4598",
                "title": "Cursor researching: Make every mb use the same component",
            },
        )

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-4598",
                "title": "Normalize status names",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: Normalize status names")

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4598",
                "title": "Existing work",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4598",
                "title": "Existing work",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4598",
                "title": "cursor researching: Existing work",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4598",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4598",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_handles_change_objects_for_workflow_state(self):
        event = {
            "type": "Issue Updated",
            "changes": [
                {
                    "field": "workflowState",
                    "newValue": {"name": "To Research"},
                }
            ],
            "issueId": "POI-4598",
            "title": "Changed workflow state",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed workflow state",
        )

    def test_requires_issue_id_and_title(self):
        missing_issue_id = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing id",
        }
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4598",
        }

        self.assertIsNone(build_issue_title_update(missing_issue_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_cli_prints_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4598",
            "title": "CLI issue",
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
                "issueId": "POI-4598",
                "title": "Cursor researching: CLI issue",
            },
        )

    def test_cli_stays_quiet_when_no_action_is_needed(self):
        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps({}),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
