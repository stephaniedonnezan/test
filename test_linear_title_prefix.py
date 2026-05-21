import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "[Backend] DeliveryTransportSegmentEntity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: [Backend] DeliveryTransportSegmentEntity",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4703",
                "title": "Implement data model",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement data model",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4703",
                "title": "Implement data model",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Implement data model")

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "cursor researching: Implement data model",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4703",
                "title": "Implement data model",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Implement data model",
            },
        )

    def test_skips_generic_update_when_status_did_not_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["assignee"],
            "data": {
                "id": "issue-uuid",
                "title": "Implement data model",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_updated_from_status_metadata(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "id": "issue-uuid",
                "title": "Implement data model",
                "workflowState": {"name": "toResearch"},
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Implement data model")

    def test_trims_title_and_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4703 ",
                "title": "  Implement data model  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement data model",
            },
        )

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement data model",
            }
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
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement data model",
            },
        )


if __name__ == "__main__":
    unittest.main()
