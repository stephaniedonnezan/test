import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_on_to_research(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5110",
                    "title": "Add processing mode column",
                }
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-5110",
                "title": f"{PREFIX}: Add processing mode column",
            },
        )

    def test_status_matching_accepts_camel_case(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-1",
                "title": "Normalize status names",
            }
        )

        self.assertEqual(action["title"], f"{PREFIX}: Normalize status names")

    def test_ignores_non_research_status(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "DEV",
                        "id": "POI-5110",
                        "title": "Add processing mode column",
                    }
                }
            )
        )

    def test_ignores_non_status_trigger(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "issueId": "POI-2",
                    "title": "Comment only",
                }
            )
        )

    def test_avoids_duplicate_prefix_case_insensitively(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-3",
                    "title": "cursor researching: Already marked",
                }
            )
        )

    def test_handles_nested_linear_issue_update_with_updated_fields(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-4",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-4")
        self.assertEqual(action["title"], f"{PREFIX}: Nested Linear payload")

    def test_ignores_generic_update_without_status_field_change(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["description"],
                    "data": {
                        "identifier": "POI-5",
                        "title": "Description update",
                        "state": {"name": "To Research"},
                    },
                }
            )
        )

    def test_handles_changes_payload(self):
        action = build_issue_title_update(
            {
                "action": "Issue Updated",
                "data": {
                    "issue": {
                        "identifier": "POI-6",
                        "title": "Changes payload",
                    }
                },
                "changes": {"state": {"new": {"name": "To Research"}}},
            }
        )

        self.assertEqual(action["title"], f"{PREFIX}: Changes payload")

    def test_requires_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_requires_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-7",
                }
            )
        )

    def test_wrapper_delegates_to_builder(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-8",
            "title": "Wrapper",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


class CliTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "CLI payload",
            }
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
                "issueId": "POI-9",
                "title": f"{PREFIX}: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
