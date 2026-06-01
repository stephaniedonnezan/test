import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_issue_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4783",
            "title": "Error while loading allocation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4783",
                "title": "Cursor researching: Error while loading allocation",
            },
        )

    def test_accepts_flat_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-1234",
                "title": "Investigate failed allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate failed allocation",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "identifier": "POI-4321",
                "title": "Research allocation page failure",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4321",
                "title": "Cursor researching: Research allocation page failure",
            },
        )

    def test_ignores_non_research_status(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "QA",
                    "id": "POI-4783",
                    "title": "Error while loading allocation",
                }
            )
        )

    def test_ignores_non_status_update(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["title"],
                    "status": "to research",
                    "id": "POI-4783",
                    "title": "Error while loading allocation",
                }
            )
        )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-4783",
                    "title": "cursor researching: Error while loading allocation",
                }
            )
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4783",
                }
            )
        )

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4783",
            "title": "Error while loading allocation",
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
                "issueId": "POI-4783",
                "title": "Cursor researching: Error while loading allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
