import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_event(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4679",
                    "title": "Edit Input button missing container logic mass balance",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4679",
                "title": (
                    "Cursor researching: "
                    "Edit Input button missing container logic mass balance"
                ),
            },
        )

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "In Review",
                    "id": "POI-4679",
                    "title": "Edit Input button missing container logic mass balance",
                }
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_trigger(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-4679",
                    "title": "Edit Input button missing container logic mass balance",
                }
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to-research",
                    "id": "POI-4679",
                    "title": "cursor researching: Existing title",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4679",
                "title": "cursor researching: Existing title",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-4679",
                        "title": (
                            "Edit Input button missing container logic mass balance"
                        ),
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4679",
                "title": (
                    "Cursor researching: "
                    "Edit Input button missing container logic mass balance"
                ),
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "identifier": "POI-4679",
                        "title": "Edit Input button",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(update)

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4679",
                "title": "Edit Input button",
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
                "issueId": "POI-4679",
                "title": "Cursor researching: Edit Input button",
            },
        )


if __name__ == "__main__":
    unittest.main()
