import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "POST /qualified-input failed with status code 400",
            "id": "POI-3671",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3671",
                "title": "Cursor researching: POST /qualified-input failed with status code 400",
            },
        )

    def test_reads_automation_trigger_context_wrapper(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Investigate request validation failure",
                "id": "POI-3671",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3671")
        self.assertEqual(
            update["title"],
            "Cursor researching: Investigate request validation failure",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "title": "Investigate request validation failure",
            "id": "POI-3671",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_trigger_types(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "title": "Investigate request validation failure",
            "id": "POI-3671",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "cursor researching: Investigate request validation failure",
            "id": "POI-3671",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Investigate request validation failure",
        )

    def test_normalizes_status_and_trigger_formatting(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "title": "Investigate request validation failure",
            "issueId": "POI-3671",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate request validation failure",
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-3671",
                    "title": "Investigate request validation failure",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3671",
                "title": "Cursor researching: Investigate request validation failure",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Investigate request validation failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate request validation failure",
                "id": "POI-3671",
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
                "issueId": "POI-3671",
                "title": "Cursor researching: Investigate request validation failure",
            },
        )


if __name__ == "__main__":
    unittest.main()
