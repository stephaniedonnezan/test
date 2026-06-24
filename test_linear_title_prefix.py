import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4874",
            "title": "Containers tab action bar has empty lane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )

    def test_reads_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4874",
                    "title": "Containers tab action bar",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar",
            },
        )

    def test_accepts_separator_and_case_variants_for_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-4874",
            "title": "Research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research issue",
        )

    def test_uses_nested_linear_issue_payload_for_generic_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4874",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_supports_change_payload_new_value(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "issue": {
                "identifier": "POI-4874",
                "title": "Changed workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed workflow state",
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4874",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4874",
            "title": "Title update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4874",
            "title": "QA issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4874",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4874 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4874",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4874",
                "title": "CLI issue",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
