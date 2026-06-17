import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4971",
                "title": "E-mail verification after account setup",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4971",
                "title": "Cursor researching: E-mail verification after account setup",
            },
        )

    def test_accepts_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-4971",
                "title": "Email verification",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4971",
                "title": "Cursor researching: Email verification",
            },
        )

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4971",
                    "title": "E-mail verification after account setup",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4971",
                "title": "Cursor researching: E-mail verification after account setup",
            },
        )

    def test_reads_changed_status_metadata(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "id": "linear-id",
                    "identifier": "POI-4971",
                    "title": "Email verification",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-id",
                "title": "Cursor researching: Email verification",
            },
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4971",
                "title": "Email verification",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4971",
                "title": "Email verification",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4971",
                "title": "cursor researching: Email verification",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Email verification",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4971",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4971",
                "title": "Email verification",
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
                "issueId": "POI-4971",
                "title": "Cursor researching: Email verification",
            },
        )


if __name__ == "__main__":
    unittest.main()
