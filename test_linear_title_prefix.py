import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4840",
                "title": "UBA line 34 - 46 are probably wrong",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4840",
                "title": "Cursor researching: UBA line 34 - 46 are probably wrong",
            },
        )

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4840",
                "title": "UBA line 34 - 46 are probably wrong",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA line 34 - 46 are probably wrong",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4840",
                "title": "UBA line 34 - 46 are probably wrong",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4840",
                "title": "UBA line 34 - 46 are probably wrong",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4840",
                "title": "cursor researching: UBA line 34 - 46 are probably wrong",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4840",
                    "title": "UBA line 34 - 46 are probably wrong",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4840",
                "title": "Cursor researching: UBA line 34 - 46 are probably wrong",
            },
        )

    def test_reads_status_from_change_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "id": "POI-4840",
                    "title": "UBA line 34 - 46 are probably wrong",
                },
                "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA line 34 - 46 are probably wrong",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4840",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4840",
                "title": "UBA line 34 - 46 are probably wrong",
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
                "issueId": "POI-4840",
                "title": "Cursor researching: UBA line 34 - 46 are probably wrong",
            },
        )


if __name__ == "__main__":
    unittest.main()
