import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3091",
            "title": "[FE] Dialog refinment",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )

    def test_prefixes_cloud_automation_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3091",
                    "title": "[FE] Dialog refinment",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-3091")
        self.assertEqual(update["title"], "Cursor researching: [FE] Dialog refinment")

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-3091",
            "title": "[FE] Dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3091",
            "title": "[FE] Dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-3091",
            "title": "cursor researching: [FE] Dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case(self):
        event = {
            "trigger": "stateChanged",
            "newStatus": "ToResearch",
            "id": "POI-3091",
            "title": "Dialog refinment",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Dialog refinment")

    def test_uses_linear_identifier_instead_of_uuid(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "f6f9e25b-010d-4694-8c20-9e3948f0f70f",
                "identifier": "POI-3091",
                "title": "[FE] Dialog refinment",
                "state": {"name": "to research"},
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3091")

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-3091",
                "title": "[FE] Dialog refinment",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"newValue": {"name": "To Research"}}},
            "identifier": "POI-3091",
            "title": "[FE] Dialog refinment",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: [FE] Dialog refinment")

    def test_reads_workflow_state_name(self):
        event = {
            "webhookType": "updated_issue",
            "updatedFields": [{"name": "workflowState"}],
            "identifier": "POI-3091",
            "title": "[FE] Dialog refinment",
            "workflowState": {"name": "to-research"},
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: [FE] Dialog refinment")

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-3091 ",
            "title": "  [FE] Dialog refinment  ",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3091")
        self.assertEqual(update["title"], "Cursor researching: [FE] Dialog refinment")

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "x"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "x"}
            )
        )

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )


if __name__ == "__main__":
    unittest.main()
