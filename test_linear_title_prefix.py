import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4034",
                "title": "The grouping by trip errors",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4034",
                "title": "Cursor researching: The grouping by trip errors",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4034",
                "title": "The grouping by trip errors",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4034",
                "title": "The grouping by trip errors",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4034",
                "title": "cursor researching: The grouping by trip errors",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4034",
                "title": "cursor researching: The grouping by trip errors",
            },
        )

    def test_normalizes_research_status_variants(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4034",
                "title": "Research me",
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Cursor researching: Research me")

    def test_handles_nested_linear_issue_update_payloads(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-4034",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4034",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_ignores_generic_issue_updates_without_status_changes(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4034",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self) -> None:
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Todo"},
                    "newValue": {"name": "To Research"},
                },
            },
            "data": {
                "issue": {
                    "identifier": "POI-4034",
                    "title": "Changed status issue",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4034",
                "title": "Cursor researching: Changed status issue",
            },
        )

    def test_cli_prints_action_json(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4034",
                "title": "CLI issue",
            },
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4034",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
