import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_entering_research(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4212",
                "title": "Display CO2 balance on frontend MB",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4212",
                "title": "Cursor researching: Display CO2 balance on frontend MB",
            },
        )

    def test_ignores_status_changed_event_for_other_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4212",
                "title": "Display CO2 balance on frontend MB",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_trigger(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4212",
                "title": "Display CO2 balance on frontend MB",
            }
        )

        self.assertIsNone(result)

    def test_avoids_duplicate_prefix_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "issueId": "POI-4212",
                "title": "cursor researching: Display CO2 balance on frontend MB",
            }
        )

        self.assertIsNone(result)

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch", "  TO RESEARCH  "):
            with self.subTest(status=status):
                result = build_issue_title_update(
                    {
                        "trigger": "statusChanged",
                        "newStatus": status,
                        "identifier": "POI-4212",
                        "title": "Display CO2 balance on frontend MB",
                    }
                )

                self.assertEqual(result["issueId"], "POI-4212")
                self.assertEqual(
                    result["title"],
                    "Cursor researching: Display CO2 balance on frontend MB",
                )

    def test_supports_nested_automation_trigger_context(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-123",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4212",
                    "title": "Display CO2 balance on frontend MB",
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-4212")
        self.assertEqual(
            result["title"],
            "Cursor researching: Display CO2 balance on frontend MB",
        )

    def test_supports_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["stateId"],
                "data": {
                    "issue": {
                        "id": "issue-uuid",
                        "identifier": "POI-4212",
                        "title": "Display CO2 balance on frontend MB",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Display CO2 balance on frontend MB",
            },
        )

    def test_requires_status_field_for_generic_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "id": "issue-uuid",
                        "title": "Display CO2 balance on frontend MB",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "A title"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4212"}
            )
        )

    def test_cli_prints_update_action_for_stdin_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4212",
            "title": "Display CO2 balance on frontend MB",
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
                "issueId": "POI-4212",
                "title": "Cursor researching: Display CO2 balance on frontend MB",
            },
        )


if __name__ == "__main__":
    unittest.main()
