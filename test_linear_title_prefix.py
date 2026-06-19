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
                "id": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5077",
                "title": "Cursor researching: QA report - POI-4878 LPH without BOP",
            },
        )

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: QA report - POI-4878 LPH without BOP",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5077",
                "title": "Cursor researching: QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_changed_status_values(self):
        event = {
            "type": "update",
            "changes": {"status": {"newValue": "to research"}},
            "data": {
                "issue": {
                    "identifier": "POI-5077",
                    "title": "QA report - POI-4878 LPH without BOP",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: QA report - POI-4878 LPH without BOP",
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFrom": {"state": {"name": "Backlog"}},
                "issue": {
                    "identifier": "POI-5077",
                    "title": "QA report - POI-4878 LPH without BOP",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: QA report - POI-4878 LPH without BOP",
        )

    def test_handles_updated_fields_with_current_status(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5077",
                    "title": "QA report - POI-4878 LPH without BOP",
                    "workflowState": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5077",
        )

    def test_prefers_identifier_over_linear_uuid(self):
        event = {
            "action": "update",
            "data": {
                "updatedFrom": {"state": {"name": "Backlog"}},
                "issue": {
                    "id": "705af311-c6ef-4a21-87ff-c54d73dd5a86",
                    "identifier": "POI-5077",
                    "title": "QA report - POI-4878 LPH without BOP",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5077",
        )

    def test_ignores_missing_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5077",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
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
                "issueId": "POI-5077",
                "title": "Cursor researching: QA report - POI-4878 LPH without BOP",
            },
        )


if __name__ == "__main__":
    unittest.main()
