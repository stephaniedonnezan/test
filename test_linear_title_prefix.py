import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4895",
                "title": "improve cascade rules for the psqo entity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4895",
            "title": "improve cascade rules for the psqo entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4895",
            "title": "improve cascade rules for the psqo entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4895",
            "title": "cursor researching: improve cascade rules for the psqo entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_change_from_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "state": {"name": "to-research"},
            "identifier": "POI-4895",
            "title": "improve cascade rules for the psqo entity",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )

    def test_accepts_nested_linear_issue_payloads(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "updatedFields": ["workflowState"],
                "issue": {
                    "identifier": "POI-4895",
                    "title": "improve cascade rules for the psqo entity",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4895",
            "title": "improve cascade rules for the psqo entity",
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
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )


if __name__ == "__main__":
    unittest.main()
