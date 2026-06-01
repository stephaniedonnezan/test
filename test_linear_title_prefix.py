import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
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
                "title": "Figure out how to handle the breakdown of certificates",
                "id": "POI-3806",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
            },
        )

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "workflowState": {"name": "To Research"},
            "issue": {
                "identifier": "POI-3806",
                "title": "Figure out how to handle the breakdown of certificates",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
            },
        )

    def test_accepts_linear_update_action_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": {"workflowState": {"name": "To Research"}},
            "workflowState": {"name": "To Research"},
            "data": {
                "identifier": "POI-3806",
                "title": "Figure out how to handle the breakdown of certificates",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
            },
        )

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Figure out how to handle the breakdown of certificates",
        )

        event["new_status"] = "to-research"
        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Figure out how to handle the breakdown of certificates",
        )

    def test_uses_nested_state_name_when_status_is_nested(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Figure out how to handle the breakdown of certificates",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3806",
            "title": "cursor researching: Figure out how to handle the breakdown of certificates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-3806 ",
            "title": " Figure out how to handle the breakdown of certificates ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
            },
        )

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Figure out how to handle the breakdown of certificates",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3806"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3806",
            "title": "Figure out how to handle the breakdown of certificates",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-3806",
                "title": "Cursor researching: Figure out how to handle the breakdown of certificates",
            },
        )


if __name__ == "__main__":
    unittest.main()
