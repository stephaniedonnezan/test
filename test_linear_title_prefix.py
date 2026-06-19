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
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_accepts_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "changes": {"workflowState": {"newValue": "to-research"}},
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_ignores_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_when_updated_fields_do_not_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "cursor researching: CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
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
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )


if __name__ == "__main__":
    unittest.main()
