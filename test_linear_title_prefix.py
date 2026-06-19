import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5031",
                "title": "Improve performance of timeZoneObject()",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_accepts_status_casing_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate slow query",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate slow query",
            },
        )

    def test_returns_none_for_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-2",
            "title": "Build feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_triggers(self):
        event = {
            "trigger": "label_changed",
            "newStatus": "To Research",
            "id": "POI-3",
            "title": "Triage feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5",
                    "title": "Clarify requirements",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Clarify requirements",
            },
        )

    def test_handles_object_shaped_updated_fields(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-6",
                "title": "Research flaky test",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Research flaky test",
            },
        )

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-7",
                "title": "Refresh docs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-8",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "No issue id",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "Check CLI",
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
                "issueId": "POI-9",
                "title": "Cursor researching: Check CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
