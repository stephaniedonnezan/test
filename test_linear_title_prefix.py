import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4728",
            "title": "CO2 mass balance, monthly carry with RFNBO",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4728",
                "title": "Cursor researching: CO2 mass balance, monthly carry with RFNBO",
            },
        )

    def test_prefixes_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Investigate fuel report",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate fuel report",
            },
        )

    def test_prefixes_nested_linear_update_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-2",
                "id": "issue-uuid",
                "title": "Check certificate matching",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check certificate matching",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-3",
            "title": "Normalize statuses",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Normalize statuses",
            },
        )

    def test_accepts_hyphenated_and_underscored_status(self):
        for status in ("to-research", "to_research"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "id": "POI-4",
                    "title": "Normalize separators",
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5",
            "title": "Already done",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-6",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
            "title": "cursor researching: Existing marker",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "No id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_reads_json_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "CLI path",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI path",
            },
        )


if __name__ == "__main__":
    unittest.main()
