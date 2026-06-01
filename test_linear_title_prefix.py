import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4481",
            "title": "On QA, Lhyfe, October 2025 we have twice the same inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4481",
                "title": (
                    "Cursor researching: On QA, Lhyfe, October 2025 "
                    "we have twice the same inputs"
                ),
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4481",
                "title": "Investigate duplicated inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4481",
                "title": "Cursor researching: Investigate duplicated inputs",
            },
        )

    def test_accepts_linear_issue_updated_payload_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4481",
                "title": "Investigate duplicated inputs",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4481",
                "title": "Cursor researching: Investigate duplicated inputs",
            },
        )

    def test_handles_camel_case_status_and_trigger(self):
        event = {
            "webhookType": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4481",
            "title": "Investigate duplicated inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4481",
                "title": "Cursor researching: Investigate duplicated inputs",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4481",
            "title": "Investigate duplicated inputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4481",
            "title": "Investigate duplicated inputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4481",
                "title": "Investigate duplicated inputs",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4481",
            "title": "cursor researching: Investigate duplicated inputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4481",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Investigate duplicated inputs",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4481",
            "title": "Investigate duplicated inputs",
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
                "issueId": "POI-4481",
                "title": "Cursor researching: Investigate duplicated inputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
