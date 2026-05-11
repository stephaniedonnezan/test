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
            "id": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2628",
                "title": "Cursor researching: Uniper feedback goldmine",
            },
        )

    def test_accepts_nested_automation_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Uniper feedback goldmine",
                "id": "POI-2628",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2628",
                "title": "Cursor researching: Uniper feedback goldmine",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-2628",
                "title": "Uniper feedback goldmine",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2628",
                "title": "Cursor researching: Uniper feedback goldmine",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Uniper feedback goldmine",
        )

    def test_uses_nested_state_name_as_status(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Uniper feedback goldmine",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2628",
            "title": "cursor researching: Uniper feedback goldmine",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-2628"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2628",
            "title": "Uniper feedback goldmine",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-2628",
                "title": "Cursor researching: Uniper feedback goldmine",
            },
        )


if __name__ == "__main__":
    unittest.main()
