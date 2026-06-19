import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_gets_prefixed(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4968",
            "title": "Multi member interruption screen needs Atmen brand and legal notice",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": (
                    "Cursor researching: Multi member interruption screen needs Atmen brand "
                    "and legal notice"
                ),
            },
        )

    def test_cursor_automation_trigger_context_payload_gets_prefixed(self):
        payload = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4968",
                "title": "Multi member interruption screen needs Atmen brand and legal notice",
                "status": "To Research",
            },
        }

        update = build_issue_title_update(payload)

        self.assertEqual(update["issueId"], "POI-4968")
        self.assertEqual(
            update["title"],
            "Cursor researching: Multi member interruption screen needs Atmen brand and legal notice",
        )

    def test_full_cloud_automation_payload_gets_prefixed(self):
        payload = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4968",
                    "title": "Multi member interruption screen needs Atmen brand and legal notice",
                    "status": "To Research",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": (
                    "Cursor researching: Multi member interruption screen needs Atmen brand "
                    "and legal notice"
                ),
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        payload = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Research this",
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Research this",
        )

    def test_uses_status_fallback_when_new_status_is_missing(self):
        payload = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-2",
            "title": "Fallback status",
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Fallback status",
        )

    def test_nested_linear_update_payload_gets_prefixed(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "12c0487b-2ad7-4ec8-bec9-000000000000",
                    "identifier": "POI-3",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_change_payload_status_value_gets_prefixed(self):
        payload = {
            "action": "update",
            "data": {
                "changes": {
                    "status": {
                        "oldValue": "Backlog",
                        "newValue": "To Research",
                    }
                },
                "issue": {
                    "identifier": "POI-4",
                    "title": "Changed status",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Changed status",
        )

    def test_status_id_change_falls_back_to_nested_state_name(self):
        payload = {
            "action": "update",
            "data": {
                "changes": {
                    "state": {
                        "oldValue": "5f31f399-f010-45f3-b14a-aaaaaaaaaaaa",
                        "newValue": "65055a48-4920-4248-a1b8-bbbbbbbbbbbb",
                    }
                },
                "issue": {
                    "identifier": "POI-5",
                    "title": "Status id",
                    "state": {"id": "65055a48-4920-4248-a1b8-bbbbbbbbbbbb", "name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Status id",
        )

    def test_non_matching_status_is_ignored(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-6",
            "title": "Wrong status",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_non_status_trigger_is_ignored(self):
        payload = {
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-7",
            "title": "Wrong trigger",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_generic_update_without_status_change_is_ignored(self):
        payload = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-8",
                    "title": "Description only",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_existing_prefix_is_not_duplicated(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "cursor researching: Already handled",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_missing_issue_id_is_ignored(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_missing_title_is_ignored(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_invalid_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class CliTest(unittest.TestCase):
    def test_cli_prints_update_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4968",
            "title": "Multi member interruption screen needs Atmen brand and legal notice",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": (
                    "Cursor researching: Multi member interruption screen needs Atmen brand "
                    "and legal notice"
                ),
            },
        )

    def test_cli_prints_nothing_for_noop_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4968",
            "title": "Already done",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
