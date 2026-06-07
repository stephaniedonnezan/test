import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_automation_payload_builds_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4224",
                "title": "Follow up - allow multiple cancellation statement upload",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4224",
                "title": (
                    "Cursor researching: "
                    "Follow up - allow multiple cancellation statement upload"
                ),
            },
        )

    def test_current_non_research_trigger_payload_is_ignored(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-4224",
                "title": "[]Follow up - allow multiple cancellation statement upload",
                "status": "Duplicate",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4224",
                "title": "Follow up",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4224",
                "title": "cursor researching: Follow up",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_accepts_camel_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4224",
                "title": "Follow up",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Follow up",
        )

    def test_nested_linear_issue_update_with_changed_state_builds_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4224",
                    "title": "Allow multiple cancellation statement upload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4224",
                "title": (
                    "Cursor researching: "
                    "Allow multiple cancellation statement upload"
                ),
            },
        )

    def test_issue_update_without_status_change_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4224",
                    "title": "Allow multiple cancellation statement upload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_mapping_can_indicate_workflow_state_change(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4224",
                    "title": "Allow multiple cancellation statement upload",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allow multiple cancellation statement upload",
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4224",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Follow up",
                    }
                }
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_prints_update_action_for_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4224",
                "title": "Follow up",
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
                "issueId": "POI-4224",
                "title": "Cursor researching: Follow up",
            },
        )

    def test_cli_prints_nothing_when_no_update_is_needed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-4224",
                "title": "Follow up",
            }
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
