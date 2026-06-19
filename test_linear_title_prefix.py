import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_trigger_context_to_research_status(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4754",
                    "title": "Cleanup test mock",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )

    def test_accepts_status_changed_camel_case_and_status_separator_variants(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": "POI-123",
                "title": "Investigate supplier mapping",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate supplier mapping")

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4754",
                "title": "Cleanup test mock",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_changed_events(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4754",
                "title": "Cleanup test mock",
            }
        )

        self.assertIsNone(result)

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4754",
                "title": "cursor researching: Cleanup test mock",
            }
        )

        self.assertIsNone(result)

    def test_reads_nested_linear_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-888",
                        "title": "Research title automation",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-888")
        self.assertEqual(result["title"], "Cursor researching: Research title automation")

    def test_reads_new_status_from_change_payload(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "changes": {"workflowState": {"newValue": {"name": "to_research"}}},
                "data": {
                    "issue": {
                        "id": "POI-321",
                        "title": "Check webhook changes",
                    }
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Check webhook changes")

    def test_ignores_generic_update_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "status": "To Research",
                "id": "POI-4754",
                "title": "Cleanup test mock",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4754",
                "title": "Cleanup test mock",
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
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )


if __name__ == "__main__":
    unittest.main()
