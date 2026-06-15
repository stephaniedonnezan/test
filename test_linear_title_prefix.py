import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_automation_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4875",
                "title": "Container Events action bar layout issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4875",
                "title": "Cursor researching: Container Events action bar layout issues",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4875",
                "title": "Container Events action bar layout issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "created",
                "status": "To Research",
                "id": "POI-4875",
                "title": "Container Events action bar layout issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4875",
                "title": "Container Events action bar layout issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Container Events action bar layout issues",
        )

    def test_uses_current_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4875",
                "title": "Container Events action bar layout issues",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4875")

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4875",
                "title": "Container Events action bar layout issues",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4875",
                "title": "Cursor researching: Container Events action bar layout issues",
            },
        )

    def test_reads_new_status_from_change_object(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "issue": {
                "identifier": "POI-4875",
                "title": "Container Events action bar layout issues",
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4875")

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4875",
                "title": "cursor researching: Container Events action bar layout issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "To Research"}}
            )
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4875",
                "title": "Container Events action bar layout issues",
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
                "issueId": "POI-4875",
                "title": "Cursor researching: Container Events action bar layout issues",
            },
        )


if __name__ == "__main__":
    unittest.main()
