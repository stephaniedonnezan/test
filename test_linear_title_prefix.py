import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_trigger_context_enters_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5043",
                    "title": "Use address autofill for offtaker creation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Use address autofill for offtaker creation",
            },
        )

    def test_direct_flat_payload_enters_research(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Investigate emissions report",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Investigate emissions report")

    def test_case_and_separator_insensitive_target_status(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "toResearch",
            "identifier": "POI-2",
            "title": "Normalize research state",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize research state",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5043",
            "title": "Use address autofill for offtaker creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Research only after status changes",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_updated_fields(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_nested_linear_update_with_changes_map(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
                "issue": {"identifier": "POI-6", "title": "Changed status map"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status map",
        )

    def test_update_without_status_marker_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-7",
                    "title": "Title changed",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        missing_id = {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
        missing_title = {"trigger": "status_changed", "newStatus": "to research", "id": "POI-8"}

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "CLI payload",
            }
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
                "issueId": "POI-9",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
