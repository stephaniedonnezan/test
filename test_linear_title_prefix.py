import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_research_prefix_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "[Refactor] Remove Water Input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: [Refactor] Remove Water Input",
            },
        )

    def test_accepts_status_casing_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-1",
            "title": "Investigate inventory sync",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate inventory sync",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4637",
                "title": "Remove Water Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "Remove Water Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-2",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-3",
                "title": "Clarify emissions source",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Clarify emissions source",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Traceability audit",
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
                "issueId": "POI-4",
                "title": "Cursor researching: Traceability audit",
            },
        )


if __name__ == "__main__":
    unittest.main()
