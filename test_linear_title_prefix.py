import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_uses_status_fallback_from_flat_payload(self):
        event = {
            "trigger": "statusChanged",
            "status": "To Research",
            "issueId": "POI-1",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4962",
            "title": "cursor researching: User role not persisiting upon invitation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("ToResearch", "to-research", "to_research", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "stateChanged",
                    "newStatus": status,
                    "id": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                }

                update = build_issue_title_update(event)

                self.assertIsNotNone(update)
                self.assertEqual(update["title"], "Cursor researching: User role not persisiting upon invitation")

    def test_nested_linear_issue_update_uses_issue_identifier(self):
        event = {
            "action": "update",
            "data": {
                "id": "webhook-event-id",
                "updatedFields": ["state"],
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_nested_linear_change_metadata_can_supply_new_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "updatedFields": ["workflowState"],
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "workflowState": {"name": "Backlog"},
                },
                "changes": {
                    "workflowState": {
                        "newValue": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issue_id": " POI-4962 ",
            "title": " User role not persisiting upon invitation ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )


if __name__ == "__main__":
    unittest.main()
