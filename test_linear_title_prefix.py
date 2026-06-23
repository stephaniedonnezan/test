import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_trigger(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_ignores_other_new_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "cursor researching: MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_trigger_and_status_values(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "ToResearch",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: MB export post QA updates",
        )

    def test_supports_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5093",
        )

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_ignores_generic_update_without_status_change_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_changes_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "state": {"name": "In Progress"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: MB export post QA updates",
        )

    def test_prefers_explicit_change_status_over_current_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": "Backlog", "to": "QA"}},
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_workflow_state_markers(self):
        event = {
            "action": "issue updated",
            "updatedFields": ["workflowState"],
            "workflowState": {"name": "to_research"},
            "issueId": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5093",
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_emits_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
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
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )


if __name__ == "__main__":
    unittest.main()
