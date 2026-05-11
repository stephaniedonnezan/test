import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2476",
            "title": "[250] Trader with Storage",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2476",
                "title": "Cursor researching: [250] Trader with Storage",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-2476",
                "title": "[250] Trader with Storage",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2476",
                "title": "Cursor researching: [250] Trader with Storage",
            },
        )

    def test_ignores_other_new_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-2476",
            "title": "[250] Trader with Storage",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-2476",
            "title": "[250] Trader with Storage",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-2476",
            "title": "cursor researching: [250] Trader with Storage",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-2476",
                "title": "[250] Trader with Storage",
                "state": {"name": "ToResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2476",
                "title": "Cursor researching: [250] Trader with Storage",
            },
        )

    def test_requires_status_field_for_generic_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-2476",
                "title": "[250] Trader with Storage",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_issue_identity_or_title_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Title"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-2476"}
            )
        )


class CommandLineTest(unittest.TestCase):
    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-2476",
            "title": "[250] Trader with Storage",
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
                "issueId": "POI-2476",
                "title": "Cursor researching: [250] Trader with Storage",
            },
        )


if __name__ == "__main__":
    unittest.main()
