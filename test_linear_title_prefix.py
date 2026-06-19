import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4826",
            "title": "Update container allocation data",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )

    def test_updates_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4826",
                    "title": "Update container allocation data in frontend",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data in frontend",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4826",
            "title": "Update container allocation data",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4826",
            "title": "Update container allocation data",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4826",
            "title": "cursor researching: Update container allocation data",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-4826",
            "title": "Update container allocation data",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )

    def test_updates_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4826",
                    "title": "Update container allocation data",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4826",
                    "title": "Update container allocation data",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changed_status_to_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "DEV", "to": {"name": "To Research"}}},
            "payload": {
                "issue": {
                    "key": "POI-4826",
                    "title": "Update container allocation data",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )

    def test_requires_issue_id_and_title(self):
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4826",
        }
        missing_id = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Update container allocation data",
        }

        self.assertIsNone(build_issue_title_update(missing_title))
        self.assertIsNone(build_issue_title_update(missing_id))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4826",
            "title": "Update container allocation data",
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
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )


if __name__ == "__main__":
    unittest.main()
