import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5070",
            "title": "AssertionError: Eex-use for CO2 should be 1 or 0",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: AssertionError: Eex-use for CO2 should be 1 or 0",
            },
        )

    def test_accepts_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5070",
                    "title": "Investigate emissions assertion",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )

    def test_ignores_statuses_other_than_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To be cancelled?",
            "id": "POI-5070",
            "title": "AssertionError: Eex-use for CO2 should be 1 or 0",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5070",
            "title": "Investigate emissions assertion",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5070",
            "title": "cursor researching: Investigate emissions assertion",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-5070",
            "title": "Investigate emissions assertion",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5070",
                    "title": "Investigate emissions assertion",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )

    def test_accepts_change_objects_with_new_status(self):
        event = {
            "webhookType": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5070",
                    "title": "Investigate emissions assertion",
                }
            },
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": "To Research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )

    def test_ignores_generic_issue_updates_without_status_change_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-5070",
                    "title": "Investigate emissions assertion",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["title"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " POI-5070 ",
            "title": "  Investigate emissions assertion  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5070",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Investigate emissions assertion",
                }
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5070",
            "title": "Investigate emissions assertion",
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
                "issueId": "POI-5070",
                "title": "Cursor researching: Investigate emissions assertion",
            },
        )


if __name__ == "__main__":
    unittest.main()
