import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_trigger_context(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5129",
            "title": "Qualified inputs is empty for methane mb export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5129",
                "title": "Cursor researching: Qualified inputs is empty for methane mb export",
            },
        )

    def test_builds_update_from_automation_trigger_wrapper(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5129",
                "title": "Qualified inputs is empty for methane mb export",
            },
        }

        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5129",
                "title": "Cursor researching: Qualified inputs is empty for methane mb export",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5129",
            "title": "Qualified inputs is empty for methane mb export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5129",
            "title": "Qualified inputs is empty for methane mb export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5129",
            "title": "cursor researching: Qualified inputs is empty for methane mb export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-5129",
            "title": "Qualified inputs is empty for methane mb export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Qualified inputs is empty for methane mb export",
        )

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5129",
                "title": "Qualified inputs is empty for methane mb export",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5129",
                "title": "Cursor researching: Qualified inputs is empty for methane mb export",
            },
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5129",
                "title": "Qualified inputs is empty for methane mb export",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_object(self):
        event = {
            "action": "updated",
            "updatedFields": [{"field": "workflowState"}],
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-5129",
                "title": "Qualified inputs is empty for methane mb export",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Qualified inputs is empty for methane mb export",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": " to-research ",
            "issue_id": " POI-5129 ",
            "title": " Qualified inputs is empty for methane mb export ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5129",
                "title": "Cursor researching: Qualified inputs is empty for methane mb export",
            },
        )

    def test_ignores_payloads_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Title"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-5129"})
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "an", "event"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5129",
                "title": "Qualified inputs is empty for methane mb export",
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
                "issueId": "POI-5129",
                "title": "Cursor researching: Qualified inputs is empty for methane mb export",
            },
        )


if __name__ == "__main__":
    unittest.main()
