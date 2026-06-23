import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5111",
                "title": "02 - libs/processor/shared - contracts & DTOs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5111",
                "title": "Cursor researching: 02 - libs/processor/shared - contracts & DTOs",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5111",
                "title": "Build processor shared contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_with_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "To Research",
                "id": "POI-5111",
                "title": "Build processor shared contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5111",
                "title": "cursor researching: Build processor shared contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-5111",
                "title": "Build processor shared contracts",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Build processor shared contracts",
        )

    def test_handles_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5111",
                "title": "Build processor shared contracts",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5111",
                "title": "Cursor researching: Build processor shared contracts",
            },
        )

    def test_ignores_generic_update_when_status_field_did_not_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5111",
                "title": "Build processor shared contracts",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_issue_identity_or_title_is_missing(self):
        event_without_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5111",
            }
        }
        event_without_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Build processor shared contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event_without_title))
        self.assertIsNone(build_issue_title_update(event_without_id))


class CliTest(unittest.TestCase):
    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5111",
                "title": "Build processor shared contracts",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5111",
                "title": "Cursor researching: Build processor shared contracts",
            },
        )


if __name__ == "__main__":
    unittest.main()
