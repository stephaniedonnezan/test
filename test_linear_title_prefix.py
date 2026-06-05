import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Methanation mb closed if available qualified inputs",
                "id": "POI-4842",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4842",
                "title": "Cursor researching: Methanation mb closed if available qualified inputs",
            },
        )

    def test_ignores_current_in_review_trigger(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Methanation mb closed if available qualified inputs",
                "id": "POI-4842",
                "status": "In Review",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Add example",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Add example",
            },
        )

    def test_skips_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event_even_with_to_research_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-3",
            "title": "Comment-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_nested_linear_issue_update_with_state_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_extracts_status_from_changes_map(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {"issue": {"id": "POI-5", "title": "Changes map payload"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Changes map payload",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Title-only payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )


class CliTest(unittest.TestCase):
    def test_cli_outputs_update_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
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

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )

    def test_cli_exits_one_without_output_for_non_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-8",
                "title": "CLI negative payload",
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
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
