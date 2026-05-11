import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3626",
            "title": "[FE]Refine the dialog(s) in the Meters Page",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": (
                    "Cursor researching: "
                    "[FE]Refine the dialog(s) in the Meters Page"
                ),
            },
        )

    def test_accepts_automation_trigger_context_shape(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
                "id": "POI-3626",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": (
                    "Cursor researching: "
                    "[FE]Refine the dialog(s) in the Meters Page"
                ),
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": (
                    "Cursor researching: "
                    "[FE]Refine the dialog(s) in the Meters Page"
                ),
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-3626",
            "title": "[FE]Refine the dialog(s) in the Meters Page",
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(
            update["title"],
            "Cursor researching: [FE]Refine the dialog(s) in the Meters Page",
        )

    def test_uses_nested_status_name(self):
        event = {
            "trigger": "status_changed",
            "status": {"name": "To Research"},
            "id": "POI-3626",
            "title": "[FE]Refine the dialog(s) in the Meters Page",
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(
            update["title"],
            "Cursor researching: [FE]Refine the dialog(s) in the Meters Page",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3626",
            "title": "[FE]Refine the dialog(s) in the Meters Page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3626",
            "title": "[FE]Refine the dialog(s) in the Meters Page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3626",
            "title": (
                "cursor researching: "
                "[FE]Refine the dialog(s) in the Meters Page"
            ),
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "[FE]Refine the dialog(s) in the Meters Page",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3626",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": (
                    "Cursor researching: "
                    "[FE]Refine the dialog(s) in the Meters Page"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
