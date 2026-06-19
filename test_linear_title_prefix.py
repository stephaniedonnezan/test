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
            "id": "POI-4313",
            "title": "Weird cancel button on the delivery dialog",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: Weird cancel button on the delivery dialog",
            },
        )

    def test_accepts_cursor_automation_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "To_Research",
                "id": "POI-4313",
                "title": "Research this",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: Research this",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4313",
            "title": "Build this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4313",
            "title": "Research this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4313",
            "title": "cursor researching: Research this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_with_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4313",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_accepts_nested_issue_object_and_change_target(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "key": "POI-4313",
                    "title": "Changed through state transition",
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: Changed through state transition",
            },
        )

    def test_accepts_payload_with_status_marker_but_no_event_name(self):
        event = {
            "updatedFrom": {"workflowState": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "identifier": "POI-4313",
                    "title": "No event name",
                    "workflowState": {"name": "ToResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: No event name",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4313",
                "title": "Description changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4313",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_computed_update(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4313",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
