import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_for_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-5050",
            "title": "cursor researching: Bug: compliant co2 mixed e_ex_use",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )

    def test_accepts_status_name_from_nested_linear_issue(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )

    def test_accepts_new_status_from_change_map(self):
        event = {
            "action": "Issue Updated",
            "identifier": "POI-5050",
            "title": "Bug: compliant co2 mixed e_ex_use",
            "changes": {
                "status": {
                    "oldValue": "Backlog",
                    "newValue": "to-research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5050",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
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
                "issueId": "POI-5050",
                "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )


if __name__ == "__main__":
    unittest.main()
