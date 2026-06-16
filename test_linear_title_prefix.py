import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_to_research(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4776",
                "title": "LHV plan 7-9",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4776",
                "title": "Cursor researching: LHV plan 7-9",
            },
        )

    def test_reads_cursor_trigger_context_payload(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-4776",
                    "title": "Hydrogen modeling",
                }
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Hydrogen modeling")

    def test_reads_nested_linear_issue_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFrom": {"stateId": "old-state-id"},
                "data": {
                    "identifier": "POI-4776",
                    "title": "Research assumptions",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4776",
                "title": "Cursor researching: Research assumptions",
            },
        )

    def test_supports_camel_case_status(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4776",
                "title": "Catalyst options",
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Catalyst options")

    def test_ignores_status_changed_to_other_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4776",
                "title": "LHV plan 7-9",
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_trigger(self):
        action = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4776",
                "title": "LHV plan 7-9",
            }
        )

        self.assertIsNone(action)

    def test_ignores_generic_update_without_status_change(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "data": {
                    "identifier": "POI-4776",
                    "title": "LHV plan 7-9",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(action)

    def test_ignores_already_prefixed_title_case_insensitively(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4776",
                "title": "cursor researching: LHV plan 7-9",
            }
        )

        self.assertIsNone(action)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "LHV plan 7-9",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4776",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4776",
            "title": "LHV plan 7-9",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4776",
                "title": "Cursor researching: LHV plan 7-9",
            },
        )


if __name__ == "__main__":
    unittest.main()
