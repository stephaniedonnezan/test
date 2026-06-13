import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3431",
                "title": "follow up bug from MVP: producer // trader MB reopening - closing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3431",
                "title": (
                    "Cursor researching: follow up bug from MVP: producer // trader "
                    "MB reopening - closing"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-3431",
                "title": "follow up bug from MVP: producer // trader MB reopening - closing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3431",
                "title": "follow up bug from MVP: producer // trader MB reopening - closing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3431",
                "title": (
                    "cursor researching: follow up bug from MVP: producer // trader "
                    "MB reopening - closing"
                ),
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-3431",
                "title": "follow up bug from MVP: producer // trader MB reopening - closing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            (
                "Cursor researching: follow up bug from MVP: producer // trader "
                "MB reopening - closing"
            ),
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3431",
                    "title": "follow up bug from MVP: producer // trader MB reopening - closing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3431",
                "title": (
                    "Cursor researching: follow up bug from MVP: producer // trader "
                    "MB reopening - closing"
                ),
            },
        )

    def test_handles_changed_status_values(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"newValue": {"name": "to research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-3431",
                    "title": "follow up bug from MVP: producer // trader MB reopening - closing",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-3431",
        )

    def test_ignores_missing_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3431",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3431",
                "title": "Research title prefix",
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
                "issueId": "POI-3431",
                "title": "Cursor researching: Research title prefix",
            },
        )


if __name__ == "__main__":
    unittest.main()
