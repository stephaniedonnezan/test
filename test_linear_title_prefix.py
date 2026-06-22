import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5090",
                "title": "Add draft toggle",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5090",
            "title": "Add draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5090",
            "title": "Add draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5090",
            "title": "cursor researching: Add draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_with_separators_and_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-5090",
            "title": "Add draft toggle",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )

    def test_reads_nested_linear_data_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5090",
                    "title": "Add draft toggle",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )

    def test_reads_status_from_changes_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["status"],
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "id": "POI-5090",
            "title": "Add draft toggle",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )

    def test_generic_issue_update_requires_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-5090",
            "title": "Add draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-5090 ",
            "title": "  Add draft toggle  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )

    def test_missing_issue_id_is_noop(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Add draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_noop(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5090",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_event_is_noop(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5090",
            "title": "Add draft toggle",
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
                "issueId": "POI-5090",
                "title": "Cursor researching: Add draft toggle",
            },
        )


if __name__ == "__main__":
    unittest.main()
