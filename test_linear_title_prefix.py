import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4957",
                "title": "Build anonymised ISCC PoS test-fixture corpus",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4957",
                "title": "Cursor researching: Build anonymised ISCC PoS test-fixture corpus",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1",
            "title": "Investigate parser fixtures",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate parser fixtures",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Review Nabisy CSV mapping",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Review Nabisy CSV mapping",
            },
        )

    def test_reads_target_status_from_change_map(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"newValue": {"name": "to_research"}}},
            "data": {
                "identifier": "POI-3",
                "title": "Collect scanned German PoS samples",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Collect scanned German PoS samples",
            },
        )

    def test_uses_current_status_when_change_metadata_identifies_status(self):
        event = {
            "webhookType": "issue",
            "updated_fields": {"workflowState": {"name": "To Research"}},
            "payload": {
                "key": "POI-4",
                "title": "Validate feedstock fixtures",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Validate feedstock fixtures",
            },
        )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "cursor researching: Existing research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing research issue",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": " to research ",
            "issue_id": " POI-6 ",
            "title": "  Normalize payload fields  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Normalize payload fields",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-7",
            "title": "Leave title unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-9",
            "title": "Description update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )
        self.assertIsNone(build_issue_title_update("not a mapping"))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
            "title": "CLI example",
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
                "issueId": "POI-10",
                "title": "Cursor researching: CLI example",
            },
        )


if __name__ == "__main__":
    unittest.main()
