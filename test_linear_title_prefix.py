import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4691",
            "title": "Deprecate the Green Power Matching frontend v1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4691",
                "title": "Cursor researching: Deprecate the Green Power Matching frontend v1",
            },
        )

    def test_accepts_flat_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4691",
                "title": "Deprecate frontend v1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4691",
                "title": "Cursor researching: Deprecate frontend v1",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "identifier": "POI-4691",
                "title": "Deprecate frontend v1",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Deprecate frontend v1",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4691",
            "title": "Deprecate frontend v1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4691",
            "title": "Deprecate frontend v1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_issue_updated_must_include_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-4691",
            "title": "Deprecate frontend v1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_new_status_takes_precedence_over_stale_status_fields(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "Todo",
            },
            "newStatus": "to research",
            "id": "POI-4691",
            "title": "Deprecate frontend v1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4691",
                "title": "Cursor researching: Deprecate frontend v1",
            },
        )

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4691",
            "title": "cursor researching: Deprecate frontend v1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to-research",
            "id": " POI-4691 ",
            "title": "  Deprecate frontend v1  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4691",
                "title": "Cursor researching: Deprecate frontend v1",
            },
        )

    def test_cli_prints_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4691",
            "title": "Deprecate frontend v1",
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
                "issueId": "POI-4691",
                "title": "Cursor researching: Deprecate frontend v1",
            },
        )


if __name__ == "__main__":
    unittest.main()
