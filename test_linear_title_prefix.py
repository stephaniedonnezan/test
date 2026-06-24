import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4620",
                "title": "Move tests from cypress to backend tests",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4620",
                "title": "Cursor researching: Move tests from cypress to backend tests",
            },
        )

    def test_accepts_status_fallback_from_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "To Research",
                "id": "POI-4620",
                "title": "Research issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4620",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        for new_status in ("to_research", "to-research", "ToResearch"):
            with self.subTest(new_status=new_status):
                event = {
                    "trigger": "status changed",
                    "newStatus": new_status,
                    "issueId": "POI-4620",
                    "title": "Research issue",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Research issue",
                )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4620",
                "title": "Move tests from cypress to backend tests",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4620",
                "title": "Research issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4620",
            "title": "cursor researching: Research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Research issue",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "id": "lin-issue-uuid",
                    "title": "Research issue",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFrom": {"stateId": "old-state-uuid"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin-issue-uuid",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_handles_changes_payload_with_new_status(self):
        event = {
            "type": "Issue Updated",
            "data": {"id": "POI-4620", "title": "Research issue"},
            "changes": {"status": {"old": "Backlog", "new": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research issue",
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "lin-issue-uuid",
                    "title": "Research issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "issueId": "POI-1"}
            )
        )

    def test_cli_prints_json_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4620",
            "title": "Research issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4620",
                "title": "Cursor researching: Research issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
