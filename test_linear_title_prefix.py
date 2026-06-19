import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4720",
                "title": "Cleanup service safe results",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4720",
                "title": "Cursor researching: Cleanup service safe results",
            },
        )

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To_Research",
                "issueId": "POI-4720",
                "title": "Cleanup service safe results",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Cleanup service safe results",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4720",
                "title": "Cleanup service safe results",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4720",
                "title": "Cleanup service safe results",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4720",
                "title": "cursor researching: Cleanup service safe results",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4720",
                    "title": "Cleanup service safe results",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4720",
                "title": "Cursor researching: Cleanup service safe results",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4720",
                    "title": "Cleanup service safe results",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "action": "issue.updated",
            "changes": {"workflowState": {"old": "Backlog", "new": "to research"}},
            "data": {
                "issue": {
                    "id": "POI-4720",
                    "title": "Cleanup service safe results",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Cleanup service safe results",
        )

    def test_prioritizes_explicit_new_status_over_stale_nested_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4720",
                "title": "Cleanup service safe results",
            },
            "data": {"issue": {"status": {"name": "DEV"}}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Cleanup service safe results",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "identifier": " POI-4720 ",
                "title": " Cleanup service safe results ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4720",
                "title": "Cursor researching: Cleanup service safe results",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4720",
                    }
                }
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4720",
                "title": "Cleanup service safe results",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4720",
                "title": "Cursor researching: Cleanup service safe results",
            },
        )


if __name__ == "__main__":
    unittest.main()
