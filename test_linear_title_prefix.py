import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cloud_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4598",
                    "title": "Make every mb use the same component",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4598",
                "title": "Cursor researching: Make every mb use the same component",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-123",
                "title": "Analyze merchant balances",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Analyze merchant balances",
        )

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-321",
                    "title": "Investigate reconciliation drift",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Investigate reconciliation drift",
            },
        )

    def test_uses_status_change_new_value(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-654",
                "title": "Research cash movement",
                "changes": {
                    "status": {
                        "from": "Todo",
                        "to": {"name": "to research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research cash movement",
        )

    def test_ignores_non_status_changed_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-777",
            "title": "Research comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-888",
            "title": "Already done",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-999",
            "title": "cursor researching: Existing research marker",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-111",
            "title": "CLI smoke test",
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
                "issueId": "POI-111",
                "title": "Cursor researching: CLI smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
