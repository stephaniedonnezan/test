import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_status_changed_to_research_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Empty link dialog if no possible allocations",
            },
        )

    def test_status_falls_back_to_current_status_for_flat_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to_research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Empty link dialog if no possible allocations",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4820",
                "title": "cursor researching: Empty link dialog if no possible allocations",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_state_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4820",
                    "title": "Empty link dialog if no possible allocations",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4820",
                "title": "Cursor researching: Empty link dialog if no possible allocations",
            },
        )

    def test_nested_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4820",
                    "title": "Empty link dialog if no possible allocations",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_payload_supplies_new_status(self):
        event = {
            "action": "issue updated",
            "data": {
                "changes": {
                    "workflowState": {
                        "from": "Todo",
                        "to": {"name": "To Research"},
                    }
                },
                "issue": {
                    "identifier": "POI-4820",
                    "title": "Empty link dialog if no possible allocations",
                    "state": {"name": "Todo"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Empty link dialog if no possible allocations",
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4820",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Empty link dialog if no possible allocations",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4820",
                "title": "Empty link dialog if no possible allocations",
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
                "issueId": "POI-4820",
                "title": "Cursor researching: Empty link dialog if no possible allocations",
            },
        )


if __name__ == "__main__":
    unittest.main()
