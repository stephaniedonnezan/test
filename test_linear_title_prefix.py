import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
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

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_are_already_prefixed(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4751",
            "title": "cursor researching: Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_RESEARCH",
            "issueId": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Knowledge support on a POS-related question",
        )

    def test_accepts_linear_update_payload_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "identifier": "POI-4751",
                "title": "Knowledge support on a POS-related question",
                "state": {"name": "To Research"},
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

    def test_ignores_linear_update_payload_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4751",
                "title": "Knowledge support on a POS-related question",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_issue_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Knowledge support on a POS-related question",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
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
