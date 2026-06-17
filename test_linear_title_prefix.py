import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_when_status_enters_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-1",
            "title": "Investigate demo seeding failure",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate demo seeding failure",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4938",
            "title": "Unable to retrieve power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4938",
            "title": "cursor researching: Unable to retrieve power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "cc9466e5-c121-4962-a94f-e02def39e517",
                    "identifier": "POI-4938",
                    "title": "Unable to retrieve power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )

    def test_accepts_status_from_change_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "to research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4938",
                    "title": "Unable to retrieve power allocation",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Unable to retrieve power allocation",
        )

    def test_requires_status_field_for_generic_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4938",
            "title": "Unable to retrieve power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title_and_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4938"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4938",
                "title": "Unable to retrieve power allocation",
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
                "issueId": "POI-4938",
                "title": "Cursor researching: Unable to retrieve power allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
