import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_accepts_nested_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4751",
                "title": "Knowledge support on a POS-related question",
                "state": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_accepts_camel_case_status_changed_trigger(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
            "status": "to research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Cursor researching: Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "cursor researching: Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
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
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )


if __name__ == "__main__":
    unittest.main()
