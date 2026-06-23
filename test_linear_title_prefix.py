import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_status_changed_to_research_returns_title_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5074",
            "title": "Input card missing on trader MB",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5074",
            "title": "Input card missing on trader MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5074",
            "title": "Input card missing on trader MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5074",
            "title": "cursor researching: Input card missing on trader MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "identifier": "POI-5074",
            "title": "Input card missing on trader MB",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )

    def test_reads_cloud_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5074",
                    "title": "Input card missing on trader MB",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )

    def test_reads_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5074",
                    "title": "Input card missing on trader MB",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["priority"],
            "data": {
                "issue": {
                    "identifier": "POI-5074",
                    "title": "Input card missing on trader MB",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_mapping(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"workflowState": {"newValue": {"name": "to research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5074",
                    "title": "Input card missing on trader MB",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5074"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Input card missing on trader MB",
                }
            )
        )

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))

    def test_cli_emits_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5074",
            "title": "Input card missing on trader MB",
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
                "issueId": "POI-5074",
                "title": "Cursor researching: Input card missing on trader MB",
            },
        )


if __name__ == "__main__":
    unittest.main()
