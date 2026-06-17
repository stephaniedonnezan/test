import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
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

    def test_status_matching_accepts_separators_and_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": " POI-4971 ",
            "title": " Account setup ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4971",
                "title": "Cursor researching: Account setup",
            },
        )

    def test_status_matching_accepts_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "identifier": "POI-4971",
            "title": "Account setup",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Account setup",
        )

    def test_uses_flat_status_fallback_for_cursor_payloads(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-4971",
            "title": "E-mail verification after account setup",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: E-mail verification after account setup",
        )

    def test_builds_update_for_nested_linear_issue_update(self):
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

    def test_builds_update_from_linear_changes_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4971",
                    "title": "E-mail verification after account setup",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: E-mail verification after account setup",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4971",
            "title": "E-mail verification after account setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4971",
            "title": "E-mail verification after account setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4971",
            "title": "cursor researching: E-mail verification after account setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4971"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4971",
                "title": "E-mail verification after account setup",
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
                "title": "Cursor researching: E-mail verification after account setup",
            },
        )


if __name__ == "__main__":
    unittest.main()
