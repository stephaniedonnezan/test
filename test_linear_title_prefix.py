import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_to_research(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4431",
                    "title": "Display total CO2e and total GO on the mass balance export",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4431",
                "title": "Cursor researching: Display total CO2e and total GO on the mass balance export",
            },
        )

    def test_ignores_status_changed_event_to_other_status(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-4431",
                    "title": "Display total CO2e and total GO on the mass balance export",
                }
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_trigger(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-4431",
                    "title": "Display total CO2e and total GO on the mass balance export",
                }
            }
        )

        self.assertIsNone(update)

    def test_ignores_existing_prefix_case_insensitively(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-4431",
                    "title": "cursor researching: Display total CO2e",
                }
            }
        )

        self.assertIsNone(update)

    def test_accepts_case_and_separator_variants_for_status(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "new_status": "TO_RESEARCH",
                    "issueId": "POI-4431",
                    "title": "Display total CO2e",
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Display total CO2e")

    def test_accepts_nested_linear_issue_updated_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-4431",
                    "title": "Display total CO2e",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4431",
                "title": "Cursor researching: Display total CO2e",
            },
        )

    def test_explicit_new_status_wins_over_nested_current_status(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "data": {
                        "id": "POI-4431",
                        "title": "Display total CO2e",
                        "state": {"name": "Backlog"},
                    },
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Display total CO2e")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Display total CO2e",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4431",
            "title": "Display total CO2e",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4431",
                "title": "Cursor researching: Display total CO2e",
            },
        )


if __name__ == "__main__":
    unittest.main()
