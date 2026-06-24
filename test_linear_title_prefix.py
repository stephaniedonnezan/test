import json
import subprocess
import sys
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_cloud_status_change_to_research_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4049",
            "title": "The audit tables randomly resize",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: The audit tables randomly resize",
            },
        )

    def test_automation_trigger_context_wrapper_is_supported(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4049",
                "title": "Wrapped trigger payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: Wrapped trigger payload",
            },
        )

    def test_nested_automation_trigger_info_wrapper_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4049",
                    "title": "Nested trigger payload",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Nested trigger payload",
        )

    def test_current_qa_status_does_not_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4049",
            "title": "The audit tables randomly resize",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_does_not_update(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4049",
            "title": "The audit tables randomly resize",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_and_trigger_normalization_accepts_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4049",
            "title": "Camel case payload",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case payload",
        )

    def test_duplicate_prefix_is_not_added(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4049",
            "title": "Cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4049",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4049",
                "title": "Nested Linear payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_generic_issue_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4049",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_object_can_provide_new_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "identifier": "POI-4049",
                "title": "Changes payload",
                "changes": {
                    "status": {
                        "oldValue": {"name": "Backlog"},
                        "newValue": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changes payload",
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "No issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4049",
                }
            )
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4049 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_cli_prints_update_action(self):
        script = Path(__file__).with_name("linear_title_prefix.py")
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4049",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
