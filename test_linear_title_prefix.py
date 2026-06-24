import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_change_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4321",
                "title": "Meters - New reading doesn't appear in list until page refresh",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4321",
                "title": (
                    "Cursor researching: "
                    "Meters - New reading doesn't appear in list until page refresh"
                ),
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-1",
                "title": "Investigate title automation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate title automation",
        )

    def test_does_not_update_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4321",
                "title": "Meters issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4321",
                "title": "Meters issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4321",
                "title": "cursor researching: Meters issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-internal-id",
                "identifier": "POI-99",
                "title": "Nested Linear payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-99",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-99",
                "title": "Nested Linear payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changed_status_takes_priority_over_current_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "changes": {"state": {"new": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-100",
                "title": "Changed state payload",
                "state": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed state payload",
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4321",
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
                "issueId": "POI-4321",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
