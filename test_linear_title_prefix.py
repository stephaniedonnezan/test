import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_issue_title_for_flat_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3734",
                "title": "Sum monthly PPA power for UBA template",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3734",
                "title": "Cursor researching: Sum monthly PPA power for UBA template",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3734",
                "title": "Sum monthly PPA power for UBA template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "title_changed",
                "newStatus": "to research",
                "id": "POI-3734",
                "title": "Sum monthly PPA power for UBA template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3734",
                "title": "cursor researching: Sum monthly PPA power for UBA template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_generic_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3734",
                    "title": "Sum monthly PPA power for UBA template",
                    "state": {"name": "To-Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3734",
                "title": "Cursor researching: Sum monthly PPA power for UBA template",
            },
        )

    def test_generic_update_requires_status_field_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-3734",
                    "title": "Sum monthly PPA power for UBA template",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_nested_issue_id_over_webhook_event_id(self):
        event = {
            "id": "webhook-event-id",
            "webhookType": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Sum monthly PPA power for UBA template",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Sum monthly PPA power for UBA template",
            },
        )

    def test_returns_none_when_required_issue_fields_are_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Sum monthly PPA power for UBA template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3734",
                "title": "Sum monthly PPA power for UBA template",
            }
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
                "issueId": "POI-3734",
                "title": "Cursor researching: Sum monthly PPA power for UBA template",
            },
        )


if __name__ == "__main__":
    unittest.main()
