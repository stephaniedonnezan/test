import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, has_research_prefix


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_trigger_context_status_change_to_research(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4464",
                "title": "Delivery event and unloading event bug",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4464",
                "title": "Cursor researching: Delivery event and unloading event bug",
            },
        )

    def test_ignores_non_research_status(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4464",
                "title": "Delivery event and unloading event bug",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_change_trigger(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4464",
                "title": "Delivery event and unloading event bug",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_does_not_duplicate_research_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4464",
                "title": "cursor researching: Delivery event and unloading event bug",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4464",
                "title": "Delivery event and unloading event bug",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Delivery event and unloading event bug",
        )

    def test_supports_nested_linear_issue_update_payload(self):
        payload = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4464",
                    "title": "Delivery event and unloading event bug",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4464",
                "title": "Cursor researching: Delivery event and unloading event bug",
            },
        )

    def test_supports_workflow_state_status_fallback(self):
        payload = {
            "trigger": "status_changed",
            "issueId": "POI-4464",
            "title": "Delivery event and unloading event bug",
            "workflowState": {"name": "to research"},
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Delivery event and unloading event bug",
        )

    def test_trims_issue_id_and_title_before_building_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4464 ",
                "title": " Delivery event and unloading event bug ",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4464",
                "title": "Cursor researching: Delivery event and unloading event bug",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4464",
                    }
                }
            )
        )

    def test_has_research_prefix_is_case_insensitive(self):
        self.assertTrue(has_research_prefix("  cursor Researching: Some issue"))
        self.assertFalse(has_research_prefix("Some issue"))

    def test_cli_prints_update_action_json(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4464",
                "title": "Delivery event and unloading event bug",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4464",
                "title": "Cursor researching: Delivery event and unloading event bug",
            },
        )


if __name__ == "__main__":
    unittest.main()
