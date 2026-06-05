import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4484",
            "title": "Rework Container Closing Tab Flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_accepts_nested_automation_trigger_context(self) -> None:
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_accepts_linear_issue_update_payload_when_state_changed(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4484",
                "title": "Research display units",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research display units",
            },
        )

    def test_normalizes_status_spacing_case_and_separators(self) -> None:
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_research",
            "id": "POI-4484",
            "title": "Research display units",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Research display units",
            },
        )

    def test_ignores_other_statuses(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-4484",
            "title": "Rework Container Closing Tab Flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_updates(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Research display units",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4484",
            "title": "cursor researching: Rework Container Closing Tab Flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_malformed_payloads(self) -> None:
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4484",
                }
            )
        )

    def test_cli_prints_update_for_valid_payload(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "id": "POI-4484",
            "title": "Fix emissions units",
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
                "issueId": "POI-4484",
                "title": "Cursor researching: Fix emissions units",
            },
        )

    def test_cli_prints_nothing_when_no_update_needed(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-4484",
            "title": "Rework Container Closing Tab Flow",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
