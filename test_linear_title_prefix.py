import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_prefixes_cursor_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5031",
                "title": "Investigate timezone cache",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Investigate timezone cache",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-5031",
                "title": "Improve performance of timeZoneObject()",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-5031",
            "title": "cursor researching: Improve performance of timeZoneObject()",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5031",
                    "title": "Improve performance of timeZoneObject()",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5031",
                    "title": "Improve performance of timeZoneObject()",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
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
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )


if __name__ == "__main__":
    unittest.main()
