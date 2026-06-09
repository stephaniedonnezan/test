import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_flat_status_change_to_research_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4772",
            "title": "In the methane excel export, use 0 instead of N/A",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": (
                    "Cursor researching: "
                    "In the methane excel export, use 0 instead of N/A"
                ),
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To-Research",
            "issueId": "POI-1",
            "title": "Research this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research this",
            },
        )

    def test_linear_nested_issue_status_change_adds_prefix(self):
        event = {
            "data": {
                "updatedFields": ["stateId"],
                "issue": {
                    "identifier": "POI-123",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_linear_data_issue_fields_directly_under_data_adds_prefix(self):
        event = {
            "data": {
                "updatedFields": ["status"],
                "identifier": "POI-456",
                "title": "Direct data payload",
                "status": {"name": "to research"},
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Direct data payload",
            },
        )

    def test_non_status_change_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-2",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_already_prefixed_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Already handled",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "CLI payload",
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
                "issueId": "POI-6",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
