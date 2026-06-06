import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_automation_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "UBA POS: version number is not incremented",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": (
                    "Cursor researching: "
                    "UBA POS: version number is not incremented"
                ),
            },
        )

    def test_current_in_progress_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4839",
                "title": "UBA POS: version number is not incremented",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "UBA POS: version number is not incremented",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_accepts_separators_and_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4839",
                "title": " Research this ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": "Cursor researching: Research this",
            },
        )

    def test_title_is_not_prefixed_twice(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "cursor researching: UBA POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_status_field_is_supported(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4839",
                "title": "UBA POS nested payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": "Cursor researching: UBA POS nested payload",
            },
        )

    def test_generic_update_without_status_change_metadata_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4839",
                "title": "UBA POS nested payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_change_map_new_value_is_supported(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-4839",
                "title": "Workflow state payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": "Cursor researching: Workflow state payload",
            },
        )

    def test_explicit_new_status_wins_over_stale_current_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "Explicit status payload",
            },
            "data": {"status": "Backlog"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": "Cursor researching: Explicit status payload",
            },
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
            }
        }
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_title))
        self.assertIsNone(build_issue_title_update(missing_id))

    def test_cli_outputs_update_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "CLI payload",
            }
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
                "issueId": "POI-4839",
                "title": "Cursor researching: CLI payload",
            },
        )

    def test_cli_exits_nonzero_without_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4839",
                "title": "CLI payload",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
