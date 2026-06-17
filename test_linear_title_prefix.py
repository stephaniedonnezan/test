import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_for_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3184",
                "title": "Enhance API for delivery GHG info on non-closed MBs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3184",
                "title": (
                    "Cursor researching: "
                    "Enhance API for delivery GHG info on non-closed MBs"
                ),
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3184",
                "title": "Enhance API for delivery GHG info on non-closed MBs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3184",
                "title": "Enhance API for delivery GHG info on non-closed MBs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-3184",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-3184",
                "title": "Investigate delivery emissions",
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Investigate delivery emissions")

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3184",
                    "title": "Estimate delivery emissions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3184",
                "title": "Cursor researching: Estimate delivery emissions",
            },
        )

    def test_ignores_generic_issue_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-3184",
                    "title": "Estimate delivery emissions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_change_mapping(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "to-research"}},
            "issue": {
                "identifier": "POI-3184",
                "title": "Estimate delivery emissions",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Estimate delivery emissions",
        )

    def test_returns_none_when_issue_identity_or_title_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_writes_action_as_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3184",
                "title": "Estimate delivery emissions",
            }
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-3184",
                "title": "Cursor researching: Estimate delivery emissions",
            },
        )


if __name__ == "__main__":
    unittest.main()
