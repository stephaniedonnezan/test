import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4631",
                "title": "Allow external RFNBO input without POS",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4631",
                "title": "Cursor researching: Allow external RFNBO input without POS",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4631",
                "title": "Allow external RFNBO input without POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_events_even_with_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4631",
                "title": "Allow external RFNBO input without POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4631",
                "title": "cursor researching: Allow external RFNBO input without POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_separator_and_case_variants(self):
        for status in ("to_research", "to-research", "TO RESEARCH", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status changed",
                        "newStatus": status,
                        "id": "POI-4631",
                        "title": "Allow external RFNBO input without POS",
                    }
                }

                result = build_issue_title_update(event)

                self.assertEqual(result["title"], "Cursor researching: Allow external RFNBO input without POS")

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4631",
                    "title": "Allow external RFNBO input without POS",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4631",
                "title": "Cursor researching: Allow external RFNBO input without POS",
            },
        )

    def test_accepts_changed_status_value_from_generic_update(self):
        event = {
            "action": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "issueId": "POI-4631",
            "title": "Allow external RFNBO input without POS",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4631",
                "title": "Cursor researching: Allow external RFNBO input without POS",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4631",
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
                        "title": "Allow external RFNBO input without POS",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4631",
                "title": "Allow external RFNBO input without POS",
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
                "issueId": "POI-4631",
                "title": "Cursor researching: Allow external RFNBO input without POS",
            },
        )


if __name__ == "__main__":
    unittest.main()
