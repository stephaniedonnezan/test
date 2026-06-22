import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5059",
            "title": "Create the new functions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": "Cursor researching: Create the new functions",
            },
        )

    def test_supports_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5059",
                    "title": "Create the new functions that the complex delivery chain will need",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": (
                    "Cursor researching: Create the new functions that the complex "
                    "delivery chain will need"
                ),
            },
        )

    def test_ignores_current_non_research_status_from_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Todo",
                    "id": "POI-5059",
                    "title": "Create the new functions",
                }
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_normalization_accepts_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "identifier": "POI-5059",
            "title": "Create the new functions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": "Cursor researching: Create the new functions",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5059",
            "title": "Create the new functions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5059",
            "title": "Create the new functions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5059",
            "title": "cursor researching: Create the new functions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5059",
                    "title": "Create the new functions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": "Cursor researching: Create the new functions",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5059",
                    "title": "Create the new functions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_extracts_new_status_from_change_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5059",
                    "title": "Create the new functions",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": "Cursor researching: Create the new functions",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5059",
            "title": "Create the new functions",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5059",
                "title": "Cursor researching: Create the new functions",
            },
        )


if __name__ == "__main__":
    unittest.main()
