import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3960",
            "title": "Improve UX/UI of adding external input",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3960",
                "title": "Cursor researching: Improve UX/UI of adding external input",
            },
        )

    def test_supports_wrapped_cursor_trigger_context(self):
        event = {
            "automationId": "example",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-3960",
                "title": "Improve UX/UI of adding external input",
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-3960")
        self.assertEqual(
            result["title"],
            "Cursor researching: Improve UX/UI of adding external input",
        )

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-3960",
            "title": "Improve UX/UI of adding external input",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Improve UX/UI of adding external input",
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3960",
                    "title": "Improve UX/UI of adding external input",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3960",
                "title": "Cursor researching: Improve UX/UI of adding external input",
            },
        )

    def test_supports_changed_field_objects(self):
        event = {
            "type": "Issue Updated",
            "changes": [{"field": "workflowState"}],
            "data": {
                "id": "linear-uuid",
                "title": "Improve UX/UI of adding external input",
                "workflowState": {"name": "TO RESEARCH"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Improve UX/UI of adding external input",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-3960",
            "title": "Improve UX/UI of adding external input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-3960",
                "title": "Improve UX/UI of adding external input",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3960",
            "title": "cursor researching: Improve UX/UI of adding external input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Improve UX/UI of adding external input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3960",
            "title": "Improve UX/UI of adding external input",
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
                "issueId": "POI-3960",
                "title": "Cursor researching: Improve UX/UI of adding external input",
            },
        )


if __name__ == "__main__":
    unittest.main()
