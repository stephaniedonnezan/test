import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_prefixes_payload_nested_under_trigger_context(self):
        payload = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": " POI-5031 ",
                "title": " Improve performance of timeZoneObject() ",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_ignores_other_statuses(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_change_triggers(self):
        payload = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        payload = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5031",
            "title": "cursor researching: Improve performance of timeZoneObject()",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_prefixes_nested_linear_issue_update_when_status_changed(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5031",
                "title": "Improve performance of timeZoneObject()",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_prefixes_nested_change_object_new_status(self):
        payload = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5031",
                    "title": "Improve performance of timeZoneObject()",
                },
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_prefixes_object_shaped_updated_fields(self):
        payload = {
            "action": "update",
            "updatedFields": [{"name": "workflowState", "newValue": "To Research"}],
            "data": {
                "identifier": "POI-5031",
                "title": "Improve performance of timeZoneObject()",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_ignores_generic_issue_update_without_status_marker(self):
        payload = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5031",
                "title": "Improve performance of timeZoneObject()",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_payloads_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-5031"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Improve performance of timeZoneObject()",
                }
            )
        )

    def test_cli_outputs_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5031",
            "title": "Improve performance of timeZoneObject()",
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )


if __name__ == "__main__":
    unittest.main()
