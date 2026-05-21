import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4661",
                "title": "Cursor researching: Exclude trading sites from the energy allocation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_researching_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4661",
                "title": "cursor researching: Exclude trading sites from the energy allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-1",
            "title": "Check separator handling",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Check separator handling",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Investigate allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate allocation",
            },
        )

    def test_requires_status_field_for_generic_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["assignee"],
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Investigate allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_detects_status_change_from_changes_map(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Investigate report",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate report",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4 ",
                "title": "  Investigate report  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Investigate report",
            },
        )

    def test_safely_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-5",
            "title": "Check CLI",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Check CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
