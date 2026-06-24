import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4233",
            "title": "Metered Reading Performance Issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4233",
                "title": "Cursor researching: Metered Reading Performance Issue",
            },
        )

    def test_builds_update_from_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4233",
                    "title": "Metered Reading Performance Issue",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4233",
                "title": "Cursor researching: Metered Reading Performance Issue",
            },
        )

    def test_normalizes_status_separators_and_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4233",
            "title": "Metered Reading Performance Issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Metered Reading Performance Issue",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4233",
            "title": "Metered Reading Performance Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4233",
            "title": "Metered Reading Performance Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4233",
            "title": "cursor researching: Metered Reading Performance Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_from_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4233",
                    "title": "Metered Reading Performance Issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4233",
                "title": "Cursor researching: Metered Reading Performance Issue",
            },
        )

    def test_builds_update_from_changes_mapping(self):
        event = {
            "action": "updated",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-4233",
                "title": "Metered Reading Performance Issue",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Metered Reading Performance Issue",
        )

    def test_builds_update_from_changes_list(self):
        event = {
            "action": "Issue Updated",
            "changes": [{"field": "workflowState", "newValue": "To Research"}],
            "issue": {
                "identifier": "POI-4233",
                "title": "Metered Reading Performance Issue",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4233",
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4233",
                "title": "Metered Reading Performance Issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4233"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4233",
            "title": "Metered Reading Performance Issue",
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
                "issueId": "POI-4233",
                "title": "Cursor researching: Metered Reading Performance Issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
