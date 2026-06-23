import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_cursor_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4693",
                "title": "WP1 - Migrate HydrogenStrategy",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4693",
                "title": "Cursor researching: WP1 - Migrate HydrogenStrategy",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "id": "POI-4693",
                "title": "WP1 - Migrate HydrogenStrategy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4693",
                "title": "WP1 - Migrate HydrogenStrategy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4693",
                "title": "cursor researching: WP1 - Migrate HydrogenStrategy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_from_nested_linear_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4693",
                    "title": "WP1 - Migrate HydrogenStrategy",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4693",
                "title": "Cursor researching: WP1 - Migrate HydrogenStrategy",
            },
        )

    def test_accepts_changed_status_value_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "to-research"}},
            "issue": {
                "issueId": "POI-4693",
                "title": "WP1 - Migrate HydrogenStrategy",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4693",
                "title": "Cursor researching: WP1 - Migrate HydrogenStrategy",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "WP1 - Migrate HydrogenStrategy",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4693",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4693",
                "title": "WP1 - Migrate HydrogenStrategy",
            }
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
                "issueId": "POI-4693",
                "title": "Cursor researching: WP1 - Migrate HydrogenStrategy",
            },
        )


if __name__ == "__main__":
    unittest.main()
