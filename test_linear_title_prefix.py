import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_cursor_status_change_trigger_context(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4787",
                "title": "inheriting transport emissions for 7911 and 7872 is still locked",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": (
                    "Cursor researching: inheriting transport emissions for 7911 "
                    "and 7872 is still locked"
                ),
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4787",
                "title": "Research title",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title",
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-4787",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_accepts_changes_payload_with_to_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4787",
                "title": "Changed workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": "Cursor researching: Changed workflow state",
            },
        )

    def test_accepts_updated_fields_payload_with_to_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4787",
                "title": "Updated fields workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": "Cursor researching: Updated fields workflow state",
            },
        )

    def test_accepts_updated_from_status_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-4787",
                "title": "State id update",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": "Cursor researching: State id update",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4787",
                "title": "Already complete title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4787",
                "title": "Comment title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4787",
                    "title": "Title-only update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_stale_nested_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4787",
                "title": "Stale nested state",
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Stale nested state",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4787",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4787",
            "title": "Alias title",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4787"}
            )
        )

    def test_cli_prints_json_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4787",
            "title": "CLI title",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4787",
                "title": "Cursor researching: CLI title",
            },
        )

    def test_cli_prints_null_for_non_matching_payload(self):
        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps({"trigger": "status_changed", "newStatus": "Done"}),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(completed.stdout.strip(), "null")


if __name__ == "__main__":
    unittest.main()
