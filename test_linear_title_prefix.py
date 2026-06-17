import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5013",
                "title": "cursor researching: Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "To-Research",
                "issueId": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Loading message goes behind Mass Balance items",
        )

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )

    def test_supports_changed_fields_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "issue": {
                "identifier": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
                "workflowState": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5013",
        )

    def test_returns_none_when_id_or_title_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5013"}
            )
        )

    def test_cli_prints_action_for_stdin_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
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
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )


if __name__ == "__main__":
    unittest.main()
