import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5063",
                "title": "Improve performance of getPossibleQualifiedOutputItemsForLoadingEvent()",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": (
                    "Cursor researching: Improve performance of "
                    "getPossibleQualifiedOutputItemsForLoadingEvent()"
                ),
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-1",
                "title": "Investigate container logic",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate container logic",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-2",
                "title": "Investigate loading event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Investigate loading event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "cursor researching: Investigate loading event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Investigate nested payload",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Investigate nested payload",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Investigate nested payload",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_mapping(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-7",
                    "title": "Investigate status change mapping",
                },
                "changes": {"status": {"from": "Backlog", "to": {"name": "toResearch"}}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Investigate status change mapping",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "Investigate CLI payload",
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
                "issueId": "POI-9",
                "title": "Cursor researching: Investigate CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
