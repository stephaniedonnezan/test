import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3877",
                "title": "Production site legal entity address",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3877",
                "title": "Cursor researching: Production site legal entity address",
            },
        )

    def test_accepts_normalized_status_and_trigger_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-1234",
                "title": "Investigate invoices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate invoices",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3877",
                "title": "Production site legal entity address",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3877",
                "title": "Production site legal entity address",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3877",
                "title": "cursor researching: Production site legal entity address",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_nested_linear_issue_webhook(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5678",
                "title": "Model a hydrogen site",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5678",
                "title": "Cursor researching: Model a hydrogen site",
            },
        )

    def test_requires_status_marker_for_generic_issue_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5678",
                "title": "Model a hydrogen site",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_detects_linear_updated_from_state_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-9876",
                "title": "Trace matching behavior",
                "state": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trace matching behavior",
        )

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"}
            )
        )


class MainTest(unittest.TestCase):
    def test_main_prints_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2468",
                "title": "Check cursor automation",
            }
        }

        with patch("sys.stdin", io.StringIO(json.dumps(payload))):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-2468",
                "title": "Cursor researching: Check cursor automation",
            },
        )


if __name__ == "__main__":
    unittest.main()
