import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handleIssueStatusChanged,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_uses_automation_trigger_context_payload_shape(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4608",
                "title": "LHV of H2 is hardcoded to 33.333",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Investigate report",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate report",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-1",
            "title": "Check edge case",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Check edge case",
            },
        )

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2",
            "title": "cursor researching: Check edge case",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-3",
            "title": "Check edge case",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_current_dev_trigger_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "status": "DEV",
                "id": "POI-4608",
                "title": "LHV of H2 is hardcoded to 33.333",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Check edge case",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_when_status_was_not_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "POI-5",
                    "title": "Check edge case",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handler_aliases_match_primary_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "Aliased handler",
        }
        expected = {
            "action": "update_issue_title",
            "issueId": "POI-7",
            "title": "Cursor researching: Aliased handler",
        }

        self.assertEqual(handle_issue_status_changed(event), expected)
        self.assertEqual(handleIssueStatusChanged(event), expected)

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-8",
            "title": "Check CLI",
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
                "issueId": "POI-8",
                "title": "Cursor researching: Check CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
