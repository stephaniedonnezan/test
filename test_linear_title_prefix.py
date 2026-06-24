import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Let users nicely visualize",
                "id": "POI-3478",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3478",
                "title": "Cursor researching: Let users nicely visualize",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "Let users nicely visualize",
                "id": "POI-3478",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Let users nicely visualize",
                "id": "POI-3478",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "title": "cursor researching: Let users nicely visualize",
                "id": "POI-3478",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "title": "Let users nicely visualize",
                "issueId": "POI-3478",
            }
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Cursor researching: Let users nicely visualize")

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-3478",
                    "title": "Let users nicely visualize",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3478",
                "title": "Cursor researching: Let users nicely visualize",
            },
        )

    def test_reads_new_status_from_change_details(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-3478",
                    "title": "Let users nicely visualize",
                    "state": {"name": "Todo"},
                }
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-3478")
        self.assertEqual(result["title"], "Cursor researching: Let users nicely visualize")

    def test_cli_prints_json_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Let users nicely visualize",
                "id": "POI-3478",
            }
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
                "issueId": "POI-3478",
                "title": "Cursor researching: Let users nicely visualize",
            },
        )


if __name__ == "__main__":
    unittest.main()
