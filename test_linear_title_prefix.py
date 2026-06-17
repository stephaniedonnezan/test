import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4988",
                "title": "Cursor researching: Container production site can be added",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-1",
                "title": "Investigate workflow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate workflow",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-2",
                "title": "Comment should not update title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "1d266f4a-8dd0-4011-8422-2e6c41ac0328",
                    "identifier": "POI-4",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_requires_status_field_on_generic_update(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Description changed",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_object(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
                "issue": {"identifier": "POI-6", "title": "Changed status payload"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status payload",
            },
        )

    def test_returns_none_when_title_or_issue_id_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "To Research"}}
            )
        )

    def test_cli_prints_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": "CLI payload",
            }
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
