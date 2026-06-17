import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Rounding error in power allocation",
                "id": "POI-4877",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Rounding error in power allocation",
                "id": "POI-4877",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Rounding error in power allocation",
                "id": "POI-4877",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "title": "cursor researching: Rounding error in power allocation",
                "id": "POI-4877",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_name(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "title": "Rounding error in power allocation",
                "issueId": "POI-4877",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_handles_nested_linear_issue_update_with_status_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4877",
                    "title": "Rounding error in power allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_handles_status_value_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"newValue": "To Research"}},
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4877",
                "title": "Rounding error in power allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4877",
                "title": "Rounding error in power allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": " ",
                        "title": "Rounding error in power allocation",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4877",
                        "title": " ",
                    }
                }
            )
        )

    def test_cli_reads_json_from_stdin(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4877",
                "title": "Rounding error in power allocation",
            }
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
                "issueId": "POI-4877",
                "title": "Cursor researching: Rounding error in power allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
