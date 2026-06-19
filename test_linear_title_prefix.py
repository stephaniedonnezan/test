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
                "newStatus": "To Research",
                "id": "POI-4382",
                "title": "Allow overrides in spreadsheets on test comparisons",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Allow overrides in spreadsheets on test comparisons",
            },
        )

    def test_supports_automation_trigger_info_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-4382",
                    "title": "Spreadsheet comparison overrides",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Spreadsheet comparison overrides",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4382",
                "title": "Spreadsheet comparison overrides",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4382",
                "title": "Spreadsheet comparison overrides",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4382",
                "title": "cursor researching: Spreadsheet comparison overrides",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "cursor researching: Spreadsheet comparison overrides",
            },
        )

    def test_supports_nested_linear_issue_update_changes(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4382",
                    "title": "Spreadsheet comparison overrides",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {"state": {"oldValue": "Backlog", "newValue": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Spreadsheet comparison overrides",
            },
        )

    def test_generic_updates_must_include_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "identifier": "POI-4382",
                    "title": "Spreadsheet comparison overrides",
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4382",
                "title": "Spreadsheet comparison overrides",
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
                "issueId": "POI-4382",
                "title": "Cursor researching: Spreadsheet comparison overrides",
            },
        )


if __name__ == "__main__":
    unittest.main()
