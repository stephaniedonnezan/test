import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_title_update_for_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3800",
            "title": "When delivery event is created",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3800",
                "title": "Cursor researching: When delivery event is created",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Add emissions details",
        }

        action = build_issue_title_update(event)

        self.assertEqual(action["title"], "Cursor researching: Add emissions details")

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-2",
            "title": "Research downstream emissions",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-2",
        )

    def test_handles_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "title": "Nested payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3800",
            "title": "When delivery event is created",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3800",
            "title": "When delivery event is created",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_when_status_was_not_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3800",
            "title": "When delivery event is created",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3800",
            "title": "cursor researching: When delivery event is created",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_required_issue_data(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3800",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3800",
                "title": "When delivery event is created",
            }
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
                "issueId": "POI-3800",
                "title": "Cursor researching: When delivery event is created",
            },
        )


if __name__ == "__main__":
    unittest.main()
