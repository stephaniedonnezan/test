import json
import subprocess
import sys
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4484",
                "title": "cursor researching: Rework Container Closing Tab Flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_accepts_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Rework Container Closing Tab Flow",
        )

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4484",
                    "title": "Rework Container Closing Tab Flow",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_accepts_changed_status_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "id": "issue-123",
                    "title": "Rework Container Closing Tab Flow",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Rework Container Closing Tab Flow",
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4484",
                    "title": "Rework Container Closing Tab Flow",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "To Research"}}
            )
        )

    def test_cli_reads_stdin_and_prints_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        completed = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("linear_title_prefix.py"))],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )


if __name__ == "__main__":
    unittest.main()
