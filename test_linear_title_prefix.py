import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5040",
                "title": "Create the SiteIsNotProcessingUnitError",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )

    def test_normalizes_research_status_variants(self):
        statuses = ["To Research", "to_research", "to-research", "toResearch"]

        for status in statuses:
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "triggerType": "linear",
                        "webhookType": "issue",
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-5040",
                        "title": "Research title",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Research title",
                )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-5040",
                "title": "Research title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5040",
                "title": "Research title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5040",
                "title": "cursor researching: Research title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-id",
                "title": "Research title",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research title",
            },
        )

    def test_uses_changes_map_for_new_status(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {"id": "issue-id", "title": "Research title"},
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title",
        )

    def test_uses_data_changes_map_for_new_status(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-id",
                "title": "Research title",
                "changes": {"status": {"old": "Backlog", "new": "to_research"}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title",
        )

    def test_uses_updated_fields_with_new_status_value(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {"id": "issue-id", "title": "Research title"},
            "updatedFields": [
                {"field": "state", "from": "Backlog", "to": {"name": "To Research"}}
            ],
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5040",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_json(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5040",
                "title": "Research title",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Research title",
            },
        )


if __name__ == "__main__":
    unittest.main()
