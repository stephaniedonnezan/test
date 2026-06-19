import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_cursor_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-5065",
                "title": "UBA POS should not be modifiable",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA POS should not be modifiable",
        )

    def test_normalizes_target_status_separators(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Research me",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research me",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "cursor researching: UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_new_status_outweighs_stale_issue_status(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "Backlog"},
                },
                "changes": {
                    "state": {
                        "old": {"name": "Backlog"},
                        "new": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA POS should not be modifiable",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_reads_stdin_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )


if __name__ == "__main__":
    unittest.main()
