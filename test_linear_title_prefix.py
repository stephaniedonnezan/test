import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5035",
                "title": "LHV versioning & traceability",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5035",
                "title": "LHV versioning & traceability",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5035",
                "title": "LHV versioning & traceability",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-5035",
            "title": "cursor researching: LHV versioning & traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status_values(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-5035",
            "title": "LHV versioning & traceability",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: LHV versioning & traceability",
        )

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5035",
                "title": "LHV versioning & traceability",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )

    def test_requires_status_field_for_generic_issue_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["priority"],
            "data": {
                "identifier": "POI-5035",
                "title": "LHV versioning & traceability",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_detects_linear_updated_from_state_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-5035",
                "title": "LHV versioning & traceability",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: LHV versioning & traceability",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": " To Research ",
            "id": " POI-5035 ",
            "title": " LHV versioning & traceability ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5035",
                "title": "LHV versioning & traceability",
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
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )


if __name__ == "__main__":
    unittest.main()
