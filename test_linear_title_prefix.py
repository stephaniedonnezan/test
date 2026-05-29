import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_cursor_trigger_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "Missing UBA POS preview in Container Logic Closing tab.",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": (
                    "Cursor researching: Missing UBA POS preview in Container "
                    "Logic Closing tab."
                ),
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-1",
                "title": "Investigate exports",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate exports",
        )

        event["triggerContext"]["newStatus"] = "to-research"
        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate exports",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4680",
                "title": "Missing UBA POS preview",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "Missing UBA POS preview",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "cursor researching: Missing UBA POS preview",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Missing UBA POS preview",
        )

    def test_supports_nested_linear_issue_payloads(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4680",
                    "title": "Missing UBA POS preview",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )

    def test_prefers_identifier_for_linear_webhook_payloads(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4680",
                    "title": "Missing UBA POS preview",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4680")

    def test_supports_updated_from_status_payloads(self):
        event = {
            "action": "update",
            "data": {
                "updatedFrom": {"workflowState": {"name": "Backlog"}},
                "issue": {
                    "identifier": "POI-4680",
                    "title": "Missing UBA POS preview",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Missing UBA POS preview",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4680",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "Missing UBA POS preview",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )


if __name__ == "__main__":
    unittest.main()
