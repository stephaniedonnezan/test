import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4765",
                "title": "Remove the fallback",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4765",
                "title": "Cursor researching: Remove the fallback",
            },
        )

    def test_accepts_status_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate balances",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate balances",
            },
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-2",
            "title": "Build feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_update_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5",
                "title": "Nested payload",
                "state": {"name": "To Research"},
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

    def test_handles_linear_updated_from_state_id(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-6",
                "title": "Updated from payload",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Updated from payload",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_outputs_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
