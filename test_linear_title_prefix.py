import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3860",
                "title": "Meter table should display sites",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-3860",
                "title": "[][Dev] - Meter table should display sites",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3860",
                "title": "Meter table should display sites",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-3860",
            "title": "cursor researching: Meter table should display sites",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-3860",
            "title": "Meter table should display sites",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Meter table should display sites",
        )

    def test_handles_nested_linear_issue_updated_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "6b3e5f84-bccb-4742-96c2-ea9f5d752c7f",
                    "identifier": "POI-3860",
                    "title": "Meter table should display sites",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-3860",
                    "title": "Meter table should display sites",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_change_record_new_value_before_current_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "old": {"name": "Backlog"},
                    "new": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-3860",
                    "title": "Meter table should display sites",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Meter table should display sites",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Meter table should display sites",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "issueId": "POI-3860",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-3860",
            "title": "Meter table should display sites",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )


if __name__ == "__main__":
    unittest.main()
