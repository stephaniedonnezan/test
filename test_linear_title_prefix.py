import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "Create the SiteIsNotProcessingUnitError",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )

    def test_prefixes_cursor_automation_trigger_context_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "webhookType": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-5040",
                    "title": "Research processing site validation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Research processing site validation",
            },
        )

    def test_accepts_camel_case_status_names(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5040",
            "title": "Handle research transition",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Handle research transition",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5040",
            "title": "Completed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "lin-issue-id",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin-issue-id",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_requires_status_field_for_generic_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "lin-issue-id",
                    "title": "Description-only update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changes_new_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "old": "Backlog",
                    "new": {"name": "To Research"},
                }
            },
            "issueId": "POI-5040",
            "title": "Changed through map",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed through map",
        )

    def test_does_not_match_old_research_status(self):
        event = {
            "trigger": "status_changed",
            "oldStatus": "To Research",
            "newStatus": "Done",
            "id": "POI-5040",
            "title": "Leaving research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_updated_fields_entries_with_new_value(self):
        event = {
            "action": "update",
            "updatedFields": [
                {
                    "field": "workflowState",
                    "newValue": "To Research",
                }
            ],
            "identifier": "POI-5040",
            "title": "Updated fields object",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5040",
        )

    def test_returns_none_for_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "CLI issue",
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
                "issueId": "POI-5040",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
