import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4944",
                "title": "HubSpot lead routing & sales handoff",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4944",
                "title": "Cursor researching: HubSpot lead routing & sales handoff",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4944",
                "title": "HubSpot routing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4944",
                "title": "Cursor researching: HubSpot routing",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4944",
                "title": "HubSpot routing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "To Research",
                "id": "POI-4944",
                "title": "HubSpot routing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4944",
                "title": "cursor researching: HubSpot routing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4944",
                    "title": "HubSpot routing",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4944",
                "title": "Cursor researching: HubSpot routing",
            },
        )

    def test_uses_change_target_for_generic_update(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {"id": "linear-uuid", "identifier": "POI-4944", "title": "HubSpot routing"},
                "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4944",
                "title": "Cursor researching: HubSpot routing",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4944",
                    "title": "HubSpot routing",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_missing_title_or_id(self):
        event = {"trigger": "status_changed", "newStatus": "To Research", "title": "HubSpot routing"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4944",
                "title": "HubSpot routing",
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
                "issueId": "POI-4944",
                "title": "Cursor researching: HubSpot routing",
            },
        )


if __name__ == "__main__":
    unittest.main()
