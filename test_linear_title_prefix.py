import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class LinearTitlePrefixTests(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4205",
                "title": "Auditor observation period",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4205",
                "title": "Cursor researching: Auditor observation period",
            },
        )

    def test_ignores_other_new_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4205",
                "title": "Auditor observation period",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4205",
                "title": "Auditor observation period",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4205",
                "title": "cursor researching: Auditor observation period",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_snake_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "identifier": "POI-4205",
                "title": "Auditor observation period",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4205",
                "title": "Cursor researching: Auditor observation period",
            },
        )

    def test_handles_linear_update_payload_with_state_name(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-4205",
                    "title": "Auditor observation period",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["stateId"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4205",
                "title": "Cursor researching: Auditor observation period",
            },
        )

    def test_handles_status_value_from_changes(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4205",
                    "title": "Auditor observation period",
                }
            },
            "changes": {
                "state": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4205",
                "title": "Cursor researching: Auditor observation period",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4205",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_json(self):
        payload = json.dumps(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4205",
                    "title": "Auditor observation period",
                }
            }
        )
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(payload)), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4205",
                "title": "Cursor researching: Auditor observation period",
            },
        )


if __name__ == "__main__":
    unittest.main()
