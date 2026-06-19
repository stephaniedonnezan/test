import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research_event(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4076",
                "title": "Fix failing Cypress tests on main",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Research export edge cases",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research export edge cases",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4076",
            "title": "Fix failing Cypress tests on main",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4076",
            "title": "Fix failing Cypress tests on main",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4076",
            "title": "cursor researching: Fix failing Cypress tests on main",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4076",
                "title": "Fix failing Cypress tests on main",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_requires_updated_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4076",
            "title": "Fix failing Cypress tests on main",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_missing_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4076"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Fix failing Cypress tests on main",
                }
            )
        )


class CliTest(unittest.TestCase):
    def test_cli_prints_matching_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4076",
            "title": "Fix failing Cypress tests on main",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )


if __name__ == "__main__":
    unittest.main()
