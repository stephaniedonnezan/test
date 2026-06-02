import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4773",
                "title": "CO2 stock",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )

    def test_accepts_status_changed_camel_case_and_status_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-123",
            "title": "Investigate feedstock",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate feedstock",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description", "workflowState"],
                "issue": {
                    "identifier": "POI-456",
                    "title": "Methane conversion",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Methane conversion",
            },
        )

    def test_ignores_status_changed_trigger_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-789",
            "title": "Ready for QA",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-789",
            "title": "Ready for research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-789",
            "title": "Description only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-101",
            "title": "cursor researching: Existing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "cursor researching: Existing",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-101",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_event(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action_for_json_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-202",
            "title": "Electrolyser sizing",
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
                "issueId": "POI-202",
                "title": "Cursor researching: Electrolyser sizing",
            },
        )


if __name__ == "__main__":
    unittest.main()
