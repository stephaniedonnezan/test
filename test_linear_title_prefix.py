import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_automation_status_change_to_research(self) -> None:
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "To Research",
                    "title": "Commodity-generalised trading",
                    "id": "POI-5107",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5107",
                "title": "Cursor researching: Commodity-generalised trading",
            },
        )

    def test_accepts_flat_trigger_context_payload(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-1",
                "title": "Investigate certificate parsing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate certificate parsing",
            },
        )

    def test_accepts_linear_issue_update_when_status_field_changed(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Research registry rules",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research registry rules",
            },
        )

    def test_accepts_status_from_changes_payload(self) -> None:
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Compare trader flows",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Compare trader flows",
            },
        )

    def test_ignores_other_statuses(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4",
            "title": "Demo QA",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-5",
            "title": "Rename issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-7"}
            )
        )

    def test_cli_prints_update_action_for_matching_event(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "CLI smoke",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
