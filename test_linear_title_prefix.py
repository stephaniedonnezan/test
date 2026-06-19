import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_updates_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4152",
                "title": "Add ID field for supply contracts",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4152",
                "title": "Cursor researching: Add ID field for supply contracts",
            },
        )

    def test_accepts_status_and_trigger_casing_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4152",
                "title": "Investigate supply contracts",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Investigate supply contracts")

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4152",
                "title": "Investigate supply contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4152",
                "title": "Investigate supply contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4152",
                "title": "cursor researching: Investigate supply contracts",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "cursor researching: Investigate supply contracts")

    def test_nested_linear_issue_update_uses_state_name(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4152",
                    "title": "Investigate supply contracts",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4152",
                "title": "Cursor researching: Investigate supply contracts",
            },
        )

    def test_nested_linear_issue_update_accepts_state_id_change_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-4152",
                    "title": "Investigate supply contracts",
                    "state": {"name": "to-research"},
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4152")

    def test_extracts_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "issueId": "POI-4152",
            "title": "Investigate supply contracts",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Investigate supply contracts")

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "issueId": "POI-4152",
            "title": "Investigate supply contracts",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate supply contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issue_id": " POI-4152 ",
                "title": " Investigate supply contracts ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4152",
                "title": "Cursor researching: Investigate supply contracts",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4152",
                "title": "Investigate supply contracts",
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
                "issueId": "POI-4152",
                "title": "Cursor researching: Investigate supply contracts",
            },
        )


if __name__ == "__main__":
    unittest.main()
