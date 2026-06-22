import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4578",
            "title": "Container logic issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4578",
                "title": "Cursor researching: Container logic issue",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4578",
                "title": "Add an input to production sites",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4578",
                "title": "Cursor researching: Add an input to production sites",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4578",
                    "title": "Container logic issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4578",
                "title": "Cursor researching: Container logic issue",
            },
        )

    def test_accepts_status_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4578",
            "title": "Container logic issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Container logic issue",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4578",
            "title": "Container logic issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4578",
                    "title": "Container logic issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4578",
            "title": "cursor researching: Container logic issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Container logic issue",
        )

    def test_returns_none_when_id_or_title_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4578"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4578",
                "title": "Container logic issue",
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
                "issueId": "POI-4578",
                "title": "Cursor researching: Container logic issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
