import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_issue_title_for_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4933",
                "title": "Add a meter as example",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )

    def test_ignores_non_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4933",
                "title": "Add a meter as example",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4933",
                "title": "Add a meter as example",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4933",
                "title": "cursor researching: Add a meter as example",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separator_and_case_variants(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-4933",
                        "title": "Add a meter as example",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Add a meter as example",
                )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4933",
                "title": "Add a meter as example",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4933")

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4933",
                    "title": "Add a meter as example",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4933",
                "title": "Add a meter as example",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_field_in_changes_mapping(self):
        event = {
            "action": "update",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "POI-4933",
                "title": "Add a meter as example",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add a meter as example",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4933",
                "title": "Add a meter as example",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4933",
                "title": "Cursor researching: Add a meter as example",
            },
        )


if __name__ == "__main__":
    unittest.main()
