import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    build_issue_title_update,
    derive_updated_title,
    prefix_research_title,
)


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Offtakers configuration (commercial targets + emissions)",
                "id": "POI-5042",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5042",
                "title": "Cursor researching: Offtakers configuration (commercial targets + emissions)",
            },
        )

    def test_accepts_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "webhookType": "issue",
                "newStatus": " To-Research ",
                "title": "Allocation rules",
                "id": "POI-1",
            }
        }

        self.assertEqual(derive_updated_title(event), "Cursor researching: Allocation rules")

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "Agent research to review",
                "title": "Allocation rules",
                "id": "POI-1",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Allocation rules",
                "id": "POI-1",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        self.assertIsNone(prefix_research_title("Cursor researching: Allocation rules"))
        self.assertIsNone(prefix_research_title("cursor researching - Allocation rules"))

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Mass balance review",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Mass balance review",
            },
        )

    def test_ignores_non_issue_webhook_types(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "comment",
                "newStatus": "to research",
                "title": "Allocation rules",
                "id": "POI-1",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        without_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Allocation rules",
            }
        }
        without_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-1",
            }
        }

        self.assertIsNone(build_issue_title_update(without_id))
        self.assertIsNone(build_issue_title_update(without_title))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Allocation rules",
                "id": "POI-1",
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
                "issueId": "POI-1",
                "title": "Cursor researching: Allocation rules",
            },
        )


if __name__ == "__main__":
    unittest.main()
