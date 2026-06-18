import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4902",
                "title": "Assert timeline consistency before delivery issuance",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4902",
                "title": "Cursor researching: Assert timeline consistency before delivery issuance",
            },
        )

    def test_ignores_status_changed_payload_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4902",
                "title": "Assert timeline consistency before delivery issuance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4902",
                "title": "Assert timeline consistency before delivery issuance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4902",
                "title": "cursor researching: Assert timeline consistency before delivery issuance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4902",
                    "title": "Assert timeline consistency before delivery issuance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4902",
                "title": "Cursor researching: Assert timeline consistency before delivery issuance",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4902",
                    "title": "Assert timeline consistency before delivery issuance",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4902",
                "title": "Cursor researching: Assert timeline consistency before delivery issuance",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "identifier": "POI-4902",
                    "title": "Assert timeline consistency before delivery issuance",
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4902",
                "title": "Assert timeline consistency before delivery issuance",
            }
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
                "issueId": "POI-4902",
                "title": "Cursor researching: Assert timeline consistency before delivery issuance",
            },
        )


if __name__ == "__main__":
    unittest.main()
