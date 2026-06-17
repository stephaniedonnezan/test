import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4949",
                "title": "Cursor researching: Sample/demo ISCC PoS document",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "id": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4949",
                "title": "cursor researching: Sample/demo ISCC PoS document",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Sample/demo ISCC PoS document",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-internal-id",
                    "identifier": "POI-4949",
                    "title": "Sample/demo ISCC PoS document",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4949",
                "title": "Cursor researching: Sample/demo ISCC PoS document",
            },
        )

    def test_uses_change_target_before_current_state(self):
        event = {
            "action": "updated issue",
            "changes": {
                "status": {"from": "Backlog", "to": "To Research"},
            },
            "data": {
                "issue": {
                    "identifier": "POI-4949",
                    "title": "Sample/demo ISCC PoS document",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Sample/demo ISCC PoS document",
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4949",
                    "title": "Sample/demo ISCC PoS document",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_change_list_objects(self):
        event = {
            "action": "update",
            "changes": [
                {"field": "workflowState", "from": "Backlog", "to": {"name": "To Research"}}
            ],
            "issue": {
                "identifier": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4949",
        )

    def test_returns_none_for_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))

    def test_cli_prints_title_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4949",
                "title": "Sample/demo ISCC PoS document",
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
                "issueId": "POI-4949",
                "title": "Cursor researching: Sample/demo ISCC PoS document",
            },
        )


if __name__ == "__main__":
    unittest.main()
