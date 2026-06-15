import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


POI_4014_TITLE = (
    "CSV generator maps reviewed ISCC JSON fields to a valid Nabisy 2025-08 export"
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4014",
                "title": POI_4014_TITLE,
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4014",
                "title": f"Cursor researching: {POI_4014_TITLE}",
            },
        )

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4014",
                "title": POI_4014_TITLE,
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"Cursor researching: {POI_4014_TITLE}",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4014",
                "title": POI_4014_TITLE,
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4014",
                "title": POI_4014_TITLE,
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4014",
                "title": f"cursor researching: {POI_4014_TITLE}",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4014",
                    "title": POI_4014_TITLE,
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4014",
                "title": f"Cursor researching: {POI_4014_TITLE}",
            },
        )

    def test_reads_status_from_change_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "id": "POI-4014",
                    "title": POI_4014_TITLE,
                },
                "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"Cursor researching: {POI_4014_TITLE}",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4014",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4014",
                "title": POI_4014_TITLE,
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
                "issueId": "POI-4014",
                "title": f"Cursor researching: {POI_4014_TITLE}",
            },
        )


if __name__ == "__main__":
    unittest.main()
