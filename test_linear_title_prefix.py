import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload_for_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4953",
                "title": "Impressum + privacy policy (DE/EN)",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4953",
                "title": "Cursor researching: Impressum + privacy policy (DE/EN)",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Review existing legal copy",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Review existing legal copy",
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-2",
            "title": "Map processors",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Map processors",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_changes(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "changes": {
                    "state": {
                        "from": {"name": "Todo"},
                        "to": {"name": "To Research"},
                    }
                },
                "issue": {
                    "id": "issue-id",
                    "identifier": "POI-3",
                    "title": "Assess analytics cookies",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Assess analytics cookies",
            },
        )

    def test_skips_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Assess retention copy",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Assess retention copy",
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Comment should not update title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-6",
            "title": "Todo should not update title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_metadata(self):
        event = {
            "action": "update",
            "data": {"updatedFields": ["title"]},
            "status": "To Research",
            "id": "POI-7",
            "title": "Title-only update should not loop",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_valid_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "CLI support",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI support",
            },
        )


if __name__ == "__main__":
    unittest.main()
