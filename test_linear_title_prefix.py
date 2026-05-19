import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_case_separators_and_camel_case(self):
        for status in ("to_research", "TO-RESEARCH", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4483",
                    "title": "Gather ETS daily prices",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Gather ETS daily prices",
                )

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "cursor researching: Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_handles_linear_updated_from_state_id_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prioritizes_explicit_new_status_over_nested_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Stale issue title",
                    "state": {"name": "In Progress"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_missing_issue_id_or_title_returns_none(self):
        base_event = {"trigger": "status_changed", "newStatus": "To Research"}

        self.assertIsNone(build_issue_title_update({**base_event, "title": "No ID"}))
        self.assertIsNone(build_issue_title_update({**base_event, "id": "POI-4483"}))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " POI-4483 ",
            "title": " Gather ETS daily prices ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
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
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
