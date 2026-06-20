import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4932",
            "title": "Improve the Stored File Transaction Delegate",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve the Stored File Transaction Delegate",
            },
        )

    def test_nested_trigger_context_is_supported(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Investigate import failures",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate import failures",
            },
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-2",
            "title": "Build feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_event_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_linear_updated_from_state_uses_current_data_state(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "POI-4",
                "title": "Research container ordering",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Research container ordering",
            },
        )

    def test_mapping_changes_payload_is_supported(self):
        event = {
            "data": {"id": "POI-5", "title": "Understand shipment states"},
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Understand shipment states",
            },
        )

    def test_list_changes_payload_is_supported(self):
        event = {
            "data": {"id": "POI-6", "title": "Trace flaky route"},
            "changes": [
                {
                    "field": "workflowState",
                    "oldValue": {"name": "Triage"},
                    "newValue": {"name": "To Research"},
                }
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Trace flaky route",
            },
        )

    def test_status_name_is_normalized(self):
        event = {
            "trigger": "status_changed",
            "new_status": "  TO_RESEARCH  ",
            "id": "POI-7",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Normalize status names",
            },
        )

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "Use the command line",
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
                "issueId": "POI-10",
                "title": "Cursor researching: Use the command line",
            },
        )


if __name__ == "__main__":
    unittest.main()
