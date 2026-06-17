import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5007",
                "title": "Weird formatting of sentence with link",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5007",
                "title": "Cursor researching: Weird formatting of sentence with link",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5007",
            "title": "Weird formatting of sentence with link",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5007",
            "title": "Weird formatting of sentence with link",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5007",
            "title": "cursor researching: Weird formatting of sentence with link",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5007",
                "title": "cursor researching: Weird formatting of sentence with link",
            },
        )

    def test_accepts_status_separators_and_camel_case(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "issueId": "POI-5007",
            "title": "Weird formatting of sentence with link",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Weird formatting of sentence with link",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "ff8ae627-60c1-49d3-b6a1-497615bfdb11",
                    "identifier": "POI-5007",
                    "title": "Weird formatting of sentence with link",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5007",
                "title": "Cursor researching: Weird formatting of sentence with link",
            },
        )

    def test_ignores_generic_update_without_status_field_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5007",
                    "title": "Weird formatting of sentence with link",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Title"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5007"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5007",
            "title": "Weird formatting of sentence with link",
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
                "issueId": "POI-5007",
                "title": "Cursor researching: Weird formatting of sentence with link",
            },
        )


if __name__ == "__main__":
    unittest.main()
