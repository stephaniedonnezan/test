import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5051",
                "title": "Create error if compliant co2 input is not set as 1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": (
                    "Cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5051",
                "title": "Create error if compliant co2 input is not set as 1",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5051",
                "title": "Create error if compliant co2 input is not set as 1",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_cursor_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5051",
                "title": (
                    "cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_name_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-5051",
            "title": "Create error if compliant co2 input is not set as 1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": (
                    "Cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFrom": {"stateId": "old-state-id"},
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-5051",
                    "title": "Create error if compliant co2 input is not set as 1",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": (
                    "Cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            },
        )

    def test_handles_generic_issue_update_with_change_map(self):
        event = {
            "webhookType": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "issueId": "POI-5051",
            "title": "Create error if compliant co2 input is not set as 1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": (
                    "Cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            },
        )

    def test_generic_update_requires_status_change_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "issueId": "POI-5051",
            "title": "Create error if compliant co2 input is not set as 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_returns_none(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": ""}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": ""}
            )
        )

    def test_non_mapping_payload_returns_none(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "an", "event"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "id": "POI-5051",
                "title": "Create error if compliant co2 input is not set as 1",
            }
        }

        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": (
                    "Cursor researching: "
                    "Create error if compliant co2 input is not set as 1"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
