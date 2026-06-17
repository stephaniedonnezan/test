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
                "newStatus": "to research",
                "id": "POI-5020",
                "title": "Issues should always try to link",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5020",
                "title": "Cursor researching: Issues should always try to link",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "triggerType": "StatusChanged",
                "status": "ToResearch",
                "id": "POI-5020",
                "title": "Check meter links",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5020",
                "title": "Cursor researching: Check meter links",
            },
        )

    def test_prefixes_nested_linear_update_payload_with_state_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "title": "Investigate contract warning",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin_123",
                "title": "Cursor researching: Investigate contract warning",
            },
        )

    def test_reads_status_from_change_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-1234",
                    "title": "Trim this title",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Trim this title",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5020",
                "title": "Issues should always try to link",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5020",
                "title": "Issues should always try to link",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "title": "Investigate contract warning",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5020",
                "title": "cursor researching: Issues should always try to link",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5020",
                "title": "Issues should always try to link",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5020",
                "title": "Cursor researching: Issues should always try to link",
            },
        )


if __name__ == "__main__":
    unittest.main()
