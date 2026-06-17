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
            "id": "POI-4987",
            "title": "Site setup & structure",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4987",
                "title": "Cursor researching: Site setup & structure",
            },
        )

    def test_prefixes_nested_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4987",
                "title": "Site setup & structure",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4987",
                "title": "Cursor researching: Site setup & structure",
            },
        )

    def test_accepts_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4987",
                "title": "Site setup & structure",
                "state": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4987",
                "title": "Cursor researching: Site setup & structure",
            },
        )

    def test_uses_changed_status_value_before_current_state(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "id": "linear-internal-id",
                "identifier": "POI-4987",
                "title": "Site setup & structure",
                "state": {"name": "Backlog"},
            },
            "updatedFields": ["state"],
            "changes": {"state": {"to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4987",
                "title": "Cursor researching: Site setup & structure",
            },
        )

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "newStatus": "to research",
            "id": "POI-4987",
            "title": "Site setup & structure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "In Progress",
            "id": "POI-4987",
            "title": "Site setup & structure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4987",
            "title": "cursor researching: Site setup & structure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4987",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Site setup & structure",
                }
            )
        )

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4987",
            "title": "Site setup & structure",
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
                "issueId": "POI-4987",
                "title": "Cursor researching: Site setup & structure",
            },
        )

    def test_cli_prints_nothing_for_non_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4987",
            "title": "Site setup & structure",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
