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
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Tidy up turn/ch4 seeders",
                "id": "POI-4658",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4658",
                "title": "Tidy up turn/ch4 seeders",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Tidy up turn/ch4 seeders",
        )

    def test_webhook_type_issue_does_not_mask_status_changed_action(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Tidy up turn/ch4 seeders",
        )

    def test_uses_state_name_when_status_is_nested(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Tidy up turn/ch4 seeders",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "cursor researching: Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4658"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
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
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )


if __name__ == "__main__":
    unittest.main()
