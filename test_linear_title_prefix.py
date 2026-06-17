import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4896",
                "title": "Cool refactor to push straight to main - `SiteFrame`",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4896",
                "title": "Cursor researching: Cool refactor to push straight to main - `SiteFrame`",
            },
        )

    def test_normalizes_status_trigger_and_status_casing(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "issueId": "POI-1",
            "title": "Normalize status values",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Normalize status values",
            },
        )

    def test_uses_status_fallback_for_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-2",
            "title": "Fallback status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Fallback status",
            },
        )

    def test_handles_nested_linear_issue_update_with_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_handles_change_payload_new_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"newValue": "to_research"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Changed status value",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Changed status value",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "issueId": "POI-4",
            "title": "Other status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-5",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-6",
            "title": "Description update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-7",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-8",
            "state": {"name": "To Research"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-9",
            "title": "CLI payload",
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
