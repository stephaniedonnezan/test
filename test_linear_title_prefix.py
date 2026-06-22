import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_status_change_to_research_adds_prefix(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5087",
                    "title": "QA report - POI-5033",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5087",
                "title": "Cursor researching: QA report - POI-5033",
            },
        )

    def test_flat_status_change_to_research_adds_prefix(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to-research",
            "issueId": "POI-1",
            "title": "Investigate feedstock inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate feedstock inputs",
            },
        )

    def test_nested_linear_change_payload_adds_prefix(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-2",
                    "title": "Review pathway emissions",
                    "state": {"name": "To Research"},
                }
            },
            "changes": {"state": {"old": {"name": "Todo"}, "new": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Review pathway emissions",
            },
        )

    def test_changed_fields_payload_adds_prefix_from_current_state(self):
        event = {
            "type": "Issue",
            "action": "update",
            "changedFields": ["workflowState"],
            "data": {
                "id": "POI-3",
                "title": "Research permit documents",
                "workflowState": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Research permit documents",
            },
        )

    def test_non_research_status_change_is_ignored(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-5087",
                    "title": "QA report - POI-5033",
                }
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_comment_trigger_with_new_status_is_ignored(self):
        event = {
            "webhookType": "issue",
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "Discuss research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_without_status_change_is_ignored(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "POI-6",
                "title": "Edited title",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_or_issue_id_is_ignored(self):
        status_change = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
        }

        self.assertIsNone(build_issue_title_update({**status_change, "title": "Missing id"}))
        self.assertIsNone(build_issue_title_update({**status_change, "id": "POI-7"}))

    def test_cli_emits_update_action(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "CLI smoke",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI smoke",
            },
        )

    def test_cli_emits_nothing_when_no_action_is_needed(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-9",
            "title": "Done issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
