import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5021",
            "title": "Add hydrogen input does not change anything in mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Add hydrogen input does not change anything in mass balance",
            },
        )

    def test_prefixes_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate missing totals",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate missing totals",
            },
        )

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-456",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Normalize status names",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-789",
            "title": "Review researched issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-101",
            "title": "Comment should not update title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-202",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-303",
                "title": "Nested webhook payload",
                "state": {"name": "To Research"},
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-303",
                "title": "Cursor researching: Nested webhook payload",
            },
        )

    def test_prefixes_change_object_new_status(self):
        event = {
            "type": "Issue Updated",
            "id": "POI-404",
            "title": "Change object payload",
            "changes": {"workflowState": {"old": "Backlog", "new": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-404",
                "title": "Cursor researching: Change object payload",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "id": "POI-505",
            "title": "Title changed only",
            "status": "to research",
            "updatedFields": ["title"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-606",
            "title": "CLI payload",
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
                "issueId": "POI-606",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
