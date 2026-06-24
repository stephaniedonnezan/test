import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4025",
            "title": "Populate Operational Data tab",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4025",
                "title": "Cursor researching: Populate Operational Data tab",
            },
        )

    def test_supports_cloud_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4025",
                "title": "Populate Operational Data tab",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4025",
                "title": "Cursor researching: Populate Operational Data tab",
            },
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4025",
                    "title": "Populate Operational Data tab",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4025",
                "title": "Cursor researching: Populate Operational Data tab",
            },
        )

    def test_uses_explicit_changed_status_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "id": "POI-4025",
                    "title": "Populate Operational Data tab",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4025",
                "title": "Cursor researching: Populate Operational Data tab",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4025",
            "title": "Populate Operational Data tab",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4025",
            "title": "Populate Operational Data tab",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "status": "toResearch",
            "id": "POI-4025",
            "title": "cursor researching: Populate Operational Data tab",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4025",
                "title": "cursor researching: Populate Operational Data tab",
            },
        )

    def test_requires_issue_identity_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Populate Operational Data tab",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4025",
                "title": "Populate Operational Data tab",
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
                "issueId": "POI-4025",
                "title": "Cursor researching: Populate Operational Data tab",
            },
        )


if __name__ == "__main__":
    unittest.main()
