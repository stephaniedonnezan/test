import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_matches_case_separator_and_camel_case_status_variants(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "issueId": "POI-1",
                    "title": "Investigate allocation",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Investigate allocation",
                )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA Backend",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "cursor researching: Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_extracts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4930",
                    "title": "Optimize offtaker fifo allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_extracts_changed_status_from_changes_map(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "to research"}},
            "issue": {
                "id": "linear-internal-id",
                "identifier": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
                "status": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Optimize offtaker fifo allocation",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )


class CliTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
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
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
