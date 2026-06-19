import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Restore DB snapshot from production in local",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "cursor researching: Restore DB snapshot from production in local",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_changed_status_values(self):
        event = {
            "type": "update",
            "changes": {"status": {"newValue": "to research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Restore DB snapshot from production in local",
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFrom": {"state": {"name": "Backlog"}},
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_issue_identifier_before_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "changes": {"workflowState": {"to": {"name": "to research"}}},
            "data": {
                "issue": {
                    "key": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                }
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4560")

    def test_ignores_missing_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
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
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )


if __name__ == "__main__":
    unittest.main()
