import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4965",
                "title": "Fetch the meter readings only once",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Fetch the meter readings only once",
            },
        )

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4965",
                "title": "Fetch the meter readings only once",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fetch the meter readings only once",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4965",
                "title": "Fetch the meter readings only once",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4965",
                "title": "Fetch the meter readings only once",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4965",
                "title": "cursor researching: Fetch the meter readings only once",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_changed_status_values(self):
        event = {
            "action": "update",
            "changes": {"status": {"newValue": "to research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Fetch the meter readings only once",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fetch the meter readings only once",
        )

    def test_handles_changed_status_after_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"after": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "key": "POI-4965",
                    "title": "Fetch the meter readings only once",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4965",
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Fetch the meter readings only once",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fetch the meter readings only once",
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Fetch the meter readings only once",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changed_fields_with_current_issue_status(self):
        event = {
            "action": "updated",
            "changedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Fetch the meter readings only once",
                    "workflowState": {"name": "To-Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fetch the meter readings only once",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4965 ",
                "title": " Fetch the meter readings only once ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Fetch the meter readings only once",
            },
        )

    def test_ignores_missing_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4965",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4965",
                "title": "Fetch the meter readings only once",
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
                "issueId": "POI-4965",
                "title": "Cursor researching: Fetch the meter readings only once",
            },
        )


if __name__ == "__main__":
    unittest.main()
