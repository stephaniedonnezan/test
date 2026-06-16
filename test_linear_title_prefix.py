import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_trigger_context_to_research_returns_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_to_research_when_event_is_not_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4938",
                "title": "cursor researching: Unable to retrieve power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separator_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": " POI-4938 ",
                "title": "  Unable to retrieve power allocation  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "id": "a-linear-uuid",
                    "identifier": "POI-4938",
                    "title": "Unable to retrieve power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_nested_linear_issue_update_requires_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4938",
                    "title": "Unable to retrieve power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_extracts_new_status_from_changes_array(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": [
                {
                    "field": "workflowState",
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            ],
            "data": {
                "issue": {
                    "identifier": "POI-4938",
                    "title": "Unable to retrieve power allocation",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_missing_issue_id_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4938",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_direct_flat_payload_is_supported(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-4938",
            "title": "Unable to retrieve power allocation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Unable to retrieve power allocation",
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
