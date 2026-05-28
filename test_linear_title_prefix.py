import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_status_changed_to_research_prefixes_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4755",
            "title": "2026-05-27-DailyReport",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4755",
                "title": "Cursor researching: 2026-05-27-DailyReport",
            },
        )

    def test_trigger_context_payload_uses_issue_id_not_wrapper_id(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4112",
                "title": "Offtaker standard delivery address",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4112",
                "title": "Cursor researching: Offtaker standard delivery address",
            },
        )

    def test_non_matching_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4755",
            "title": "2026-05-27-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matching_status_without_status_change_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-4755",
            "title": "2026-05-27-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4755",
            "title": "cursor researching: 2026-05-27-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_uses_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-issue-uuid",
                "identifier": "POI-4581",
                "title": "DPP of h2 crashing when you try to load it",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-uuid",
                "title": "Cursor researching: DPP of h2 crashing when you try to load it",
            },
        )

    def test_status_normalization_accepts_camel_and_underscores(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4735",
            "title": "Check co2 metered reading values",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Check co2 metered reading values",
        )

    def test_issue_update_without_status_field_change_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "linear-issue-uuid",
                "title": "Cleanup of methane in weighted-round-trip-strategy",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_invalid_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4750",
            "title": "Refactor production site create and update",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4750",
                "title": "Cursor researching: Refactor production site create and update",
            },
        )


if __name__ == "__main__":
    unittest.main()
