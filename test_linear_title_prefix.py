import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2861",
                "title": "Remove all mentions of RED II from the project",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2861",
                "title": "Cursor researching: Remove all mentions of RED II from the project",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "id": "POI-2861",
                "title": "Remove all mentions of RED II from the project",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-2861",
                "title": "Remove all mentions of RED II from the project",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-2861",
            "title": "cursor researching: Remove all mentions of RED II",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_linear_update_payload_with_changed_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "identifier": "POI-2861",
                "title": "Remove all mentions of RED II from the project",
                "state": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2861",
                "title": "Cursor researching: Remove all mentions of RED II from the project",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "issueId": "POI-2861",
            "title": "Remove all mentions of RED II from the project",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-2861",
                "title": "Cursor researching: Remove all mentions of RED II from the project",
            },
        )


if __name__ == "__main__":
    unittest.main()
