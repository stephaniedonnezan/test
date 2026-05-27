import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4733",
                    "title": "Custom LHV",
                }
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_ignores_non_research_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_change_trigger(self):
        action = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "status": "to_research",
                "id": "POI-4733",
                "title": "cursor researching: Custom LHV",
            }
        )

        self.assertIsNone(action)

    def test_accepts_hyphenated_and_camel_case_status(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "status": "toResearch",
                "issueId": "POI-4733",
                "title": "Custom LHV",
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Custom LHV")

    def test_handles_nested_linear_update_payload_with_state_name(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "id": "webhook-event-id",
                    "issue": {
                        "identifier": "POI-4733",
                        "title": "Custom LHV",
                        "state": {"id": "state-id", "name": "To Research"},
                    },
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-4733")
        self.assertEqual(action["title"], "Cursor researching: Custom LHV")

    def test_ignores_update_payload_without_status_field_change(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["assignee"],
                "data": {
                    "issue": {
                        "identifier": "POI-4733",
                        "title": "Custom LHV",
                        "state": {"name": "To Research"},
                    },
                },
            }
        )

        self.assertIsNone(action)

    def test_uses_outer_new_status_before_nested_existing_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "data": {
                    "issue": {
                        "identifier": "POI-4733",
                        "title": "Custom LHV",
                        "status": "Backlog",
                    }
                },
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Custom LHV")

    def test_requires_issue_id_and_title(self):
        missing_id = build_issue_title_update(
            {"trigger": "status_changed", "newStatus": "to research", "title": "Custom LHV"}
        )
        missing_title = build_issue_title_update(
            {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4733"}
        )

        self.assertIsNone(missing_id)
        self.assertIsNone(missing_title)

    def test_cli_prints_update_action_as_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4733",
            "title": "Custom LHV",
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
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )


if __name__ == "__main__":
    unittest.main()
