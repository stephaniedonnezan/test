import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3504",
            "title": "Company Insights Concept (Dashboard)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3504",
                "title": "Cursor researching: Company Insights Concept (Dashboard)",
            },
        )

    def test_builds_update_for_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3504",
                "title": "Company Insights Concept (Dashboard)",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3504")
        self.assertEqual(
            update["title"], "Cursor researching: Company Insights Concept (Dashboard)"
        )

    def test_builds_update_for_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-3504",
                    "title": "Company Insights Concept (Dashboard)",
                    "workflowState": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3504",
                "title": "Cursor researching: Company Insights Concept (Dashboard)",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3504",
            "title": "Company Insights Concept (Dashboard)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3504",
            "title": "Company Insights Concept (Dashboard)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-3504",
            "title": "cursor researching: Company Insights Concept (Dashboard)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3504"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_json_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3504",
            "title": "Company Insights Concept (Dashboard)",
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
                "issueId": "POI-3504",
                "title": "Cursor researching: Company Insights Concept (Dashboard)",
            },
        )

    def test_cli_exits_one_without_output_for_non_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3504",
            "title": "Company Insights Concept (Dashboard)",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
