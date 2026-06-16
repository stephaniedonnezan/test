import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4230",
            "title": "Sustainability Declarations in Traceability",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4230",
                "title": "Cursor researching: Sustainability Declarations in Traceability",
            },
        )

    def test_prefixes_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4230",
                "title": "Sustainability Declarations in Traceability",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4230",
                "title": "Cursor researching: Sustainability Declarations in Traceability",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4230",
            "title": "Sustainability Declarations in Traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4230",
            "title": "Sustainability Declarations in Traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4230",
            "title": "cursor researching: Sustainability Declarations in Traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4230",
            "title": "Sustainability Declarations in Traceability",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Sustainability Declarations in Traceability",
        )

    def test_prefixes_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4230",
                    "title": "Sustainability Declarations in Traceability",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4230",
                "title": "Cursor researching: Sustainability Declarations in Traceability",
            },
        )

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4230",
                    "title": "Sustainability Declarations in Traceability",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_detects_status_changes_in_changes_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4230",
                    "title": "Sustainability Declarations in Traceability",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4230",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4230",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4230",
            "title": "Sustainability Declarations in Traceability",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4230",
                "title": "Cursor researching: Sustainability Declarations in Traceability",
            },
        )


if __name__ == "__main__":
    unittest.main()
