import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5040",
                "title": "Create site error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create site error",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5040",
            "title": "Create site error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-5040",
            "title": "Create site error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "cursor researching: Create site error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "identifier": "POI-5040",
                    "title": "Create site error",
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-5040",
                        "title": "Cursor researching: Create site error",
                    },
                )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5040",
                "title": "Create site error",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create site error",
            },
        )

    def test_supports_linear_updated_from_state_id_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-5040",
                "title": "Create site error",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create site error",
            },
        )

    def test_supports_change_mapping_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "key": "POI-5040",
            "title": "Create site error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create site error",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Create site error",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5040",
                }
            )
        )


class MainTest(unittest.TestCase):
    def test_prints_update_action_for_stdin_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5040",
            "title": "Create site error",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create site error",
            },
        )


if __name__ == "__main__":
    unittest.main()
