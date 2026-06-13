import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3521",
            "title": "Wrong conversion factor on the audit KPIs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3521",
                "title": "Cursor researching: Wrong conversion factor on the audit KPIs",
            },
        )

    def test_accepts_cursor_trigger_context_wrapper(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3521",
                "title": "Wrong conversion factor on the audit KPIs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3521",
                "title": "Cursor researching: Wrong conversion factor on the audit KPIs",
            },
        )

    def test_accepts_nested_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-3521",
                "title": "Wrong conversion factor on the audit KPIs",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3521",
                "title": "Cursor researching: Wrong conversion factor on the audit KPIs",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3521",
            "title": "Wrong conversion factor on the audit KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3521",
            "title": "Wrong conversion factor on the audit KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_issue_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-3521",
                "title": "Wrong conversion factor on the audit KPIs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "id": "POI-3521",
            "title": "cursor researching: Wrong conversion factor on the audit KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3521",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3521",
            "title": "Wrong conversion factor on the audit KPIs",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3521",
                "title": "Cursor researching: Wrong conversion factor on the audit KPIs",
            },
        )


if __name__ == "__main__":
    unittest.main()
