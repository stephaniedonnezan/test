import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_status_change_to_research_adds_marker(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "[Backend] Delivery transport segments",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: [Backend] Delivery transport segments",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "TO_RESEARCH",
                "id": "POI-1",
                "title": "Add delivery migration",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add delivery migration",
        )

    def test_status_matching_accepts_camel_case(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "id": "POI-1",
                "title": "Add delivery migration",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add delivery migration",
        )

    def test_non_research_status_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4703",
                "title": "Delivery transport segments",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_update_returns_none(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-4703",
                "title": "Delivery transport segments",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"title": "Old delivery title"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_uses_new_state_name(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-4703",
                "title": "Delivery transport segments",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"state": {"name": "Backlog"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Delivery transport segments",
            },
        )

    def test_old_status_in_updated_from_is_not_used_as_target_status(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-4703",
                "title": "Delivery transport segments",
                "state": {"name": "DEV"},
            },
            "updatedFrom": {"state": {"name": "To Research"}},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_explicit_new_status_takes_priority_over_embedded_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "Delivery transport segments",
                "state": {"name": "DEV"},
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Delivery transport segments",
        )

    def test_duplicate_marker_is_not_added(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "Cursor researching: Delivery transport segments",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Delivery transport segments",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4703",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_human_readable_trigger_name_is_supported(self):
        event = {
            "triggerContext": {
                "trigger": "status changed",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "Delivery transport segments",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Delivery transport segments",
        )

    def test_cli_prints_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "Delivery transport segments",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Delivery transport segments",
            },
        )

    def test_cli_prints_null_when_no_update_is_needed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4703",
                "title": "Delivery transport segments",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIsNone(json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
