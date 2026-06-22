import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_status_changed_issue_entering_research(self):
        event = {
            "triggerType": "linear",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5045",
            "title": 'Supply contract only states "producer"',
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": 'Cursor researching: Supply contract only states "producer"',
            },
        )

    def test_prefixes_wrapped_cursor_cloud_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5045",
                    "title": '[]Supply contract only states "producer"',
                    "status": "to research",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": 'Cursor researching: []Supply contract only states "producer"',
            },
        )

    def test_prefixes_camel_case_wrapped_trigger_context(self):
        event = {
            "automationTriggerInfo": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "ToResearch",
                    "issueId": "POI-5046",
                    "title": "Import certificates cannot be approved",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5046",
                "title": "Cursor researching: Import certificates cannot be approved",
            },
        )

    def test_prefixes_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5047",
                "title": "Evidence label is unclear",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Evidence label is unclear",
            },
        )

    def test_changes_destination_status_takes_priority_over_current_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"to": "To Research", "from": "Todo"}},
            "data": {
                "identifier": "POI-5048",
                "title": "Trader contract language is confusing",
                "status": "Todo",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5048",
                "title": "Cursor researching: Trader contract language is confusing",
            },
        )

    def test_accepts_status_variants_case_and_separators(self):
        event = {
            "trigger": "status_changed",
            "new_status": "TO_RESEARCH",
            "id": "POI-5049",
            "title": "Yearly amount is required",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Yearly amount is required",
        )

    def test_ignores_non_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5045",
            "title": "Supply contract copy",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5045",
            "title": "Supply contract copy",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5050",
                "title": "Supply contract copy",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5051",
            "title": "cursor researching: Supply contract copy",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-5052"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Copy"}
            )
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-5053 ",
            "title": "  Supply contract copy  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5053",
                "title": "Cursor researching: Supply contract copy",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5054",
            "title": "CLI smoke",
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
                "issueId": "POI-5054",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
