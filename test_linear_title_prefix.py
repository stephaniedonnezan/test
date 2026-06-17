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
                "id": "POI-5019",
                "title": "Legal Entity address update does not show in POS",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5019",
                "title": "Cursor researching: Legal Entity address update does not show in POS",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5019",
                "title": "Legal Entity address update does not show in POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5019",
                "title": "Legal Entity address update does not show in POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5019",
                "title": "cursor researching: Legal Entity address update does not show in POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_case_and_separator_variations(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-5019",
                "title": "Legal Entity address update does not show in POS",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Legal Entity address update does not show in POS",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-5019",
                    "title": "Legal Entity address update does not show in POS",
                    "status": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5019",
                "title": "Cursor researching: Legal Entity address update does not show in POS",
            },
        )

    def test_handles_changed_status_new_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "oldValue": "Backlog",
                    "newValue": {"name": "to research"},
                }
            },
            "issue": {
                "key": "POI-5019",
                "title": "Legal Entity address update does not show in POS",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5019",
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5019",
                    "title": "Legal Entity address update does not show in POS",
                    "status": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_json_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5019",
            "title": "Legal Entity address update does not show in POS",
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
                "issueId": "POI-5019",
                "title": "Cursor researching: Legal Entity address update does not show in POS",
            },
        )


if __name__ == "__main__":
    unittest.main()
