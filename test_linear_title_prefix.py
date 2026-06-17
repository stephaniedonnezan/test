import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5015",
            "title": "Power allocation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5015",
                "title": "Cursor researching: Power allocation",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5015",
                "title": "Power allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5015",
                "title": "Cursor researching: Power allocation",
            },
        )

    def test_accepts_nested_linear_update_payload_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5015",
                "title": "Power allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5015",
                "title": "Cursor researching: Power allocation",
            },
        )

    def test_reads_new_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "issue": {
                "identifier": "POI-5015",
                "title": "Power allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Power allocation",
        )

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5015",
                "title": "Power allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "Agent research to review",
            "id": "POI-5015",
            "title": "Power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers_even_with_target_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5015",
            "title": "Power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5015",
            "title": "cursor researching: Power allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "id": "POI-5015",
                    "title": "Power allocation",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Power allocation",
                )

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Power allocation",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5015",
                }
            )
        )


class MainTests(unittest.TestCase):
    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5015",
            "title": "Power allocation",
        }

        with patch("sys.stdin", io.StringIO(json.dumps(event))):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5015",
                "title": "Cursor researching: Power allocation",
            },
        )

    def test_cli_prints_nothing_for_non_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "done",
            "id": "POI-5015",
            "title": "Power allocation",
        }

        with patch("sys.stdin", io.StringIO(json.dumps(event))):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(), 0)

        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
