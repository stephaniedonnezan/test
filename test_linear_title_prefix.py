import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_builds_update_from_cursor_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4932 ",
                "title": " Research task ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Research task",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4932",
                    "title": "Improve stored file transaction delegate",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_uses_new_status_from_change_details(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": "Backlog",
                    "to": "to-research",
                }
            },
            "issue": {
                "key": "POI-4932",
                "title": "Improve stored file transaction delegate",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_prefers_explicit_new_status_over_current_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "status": "To Research",
            "id": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4932",
            "title": "cursor researching: Improve stored file transaction delegate",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_events_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Improve stored file transaction delegate",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4932",
                }
            )
        )

    def test_uses_status_fallback_for_direct_status_change_event(self):
        event = {
            "trigger": "Issue Status Changed",
            "status": "toResearch",
            "identifier": "POI-4932",
            "title": "Improve stored file transaction delegate",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4932",
            "title": "Improve stored file transaction delegate",
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
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )


if __name__ == "__main__":
    unittest.main()
