import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload_for_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4517",
            "title": "Delete the S3 pos file after the transaction completes",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4517",
                "title": (
                    "Cursor researching: "
                    "Delete the S3 pos file after the transaction completes"
                ),
            },
        )

    def test_prefixes_cursor_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research imports",
                "id": "POI-1000",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1000",
                "title": "Cursor researching: Research imports",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4517",
            "title": "Delete S3 file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4517",
            "title": "Delete S3 file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "identifier": "POI-2000",
            "title": "Normalize webhook fields",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2000",
                "title": "Cursor researching: Normalize webhook fields",
            },
        )

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3000",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_update_with_changed_status(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4000",
                    "title": "Investigate failing invoice export",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4000",
                "title": "Cursor researching: Investigate failing invoice export",
            },
        )

    def test_prefers_issue_identifier_and_title_over_nested_state_metadata(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "state": {"id": "state-id", "name": "To Research"},
                    "identifier": "POI-4500",
                    "title": "Use the issue title",
                }
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4500",
                "title": "Cursor researching: Use the issue title",
            },
        )

    def test_prefixes_update_payload_with_changes_map(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5000",
                    "title": "Research retry behavior",
                }
            },
            "changes": {
                "status": {
                    "oldValue": "Backlog",
                    "newValue": "To Research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5000",
                "title": "Cursor researching: Research retry behavior",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-6000",
                    "title": "Do not change this title",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-7000"}
            )
        )

    def test_safely_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class CliTests(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8000",
            "title": "CLI payload",
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
                "issueId": "POI-8000",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
