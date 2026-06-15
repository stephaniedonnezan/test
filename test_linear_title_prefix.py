import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4013",
                "title": "AI parser extracts ISCC PoS PDF into structured JSON",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4013",
                "title": "Cursor researching: AI parser extracts ISCC PoS PDF into structured JSON",
            },
        )

    def test_status_names_are_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-1",
                "title": "Investigate parser",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Investigate parser")

    def test_non_research_status_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4013",
                "title": "AI parser extracts ISCC PoS PDF into structured JSON",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2",
                "title": "Investigate parser",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "cursor researching: Investigate parser",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_current_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["stateId"],
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_generic_issue_update_without_status_change_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-6",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Missing id",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "id": "POI-7",
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
