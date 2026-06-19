import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_research_prefix_for_cursor_status_change_payload(self):
        event = {
            "automationId": "example-automation",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4560",
            "title": "Investigate production data",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )

    def test_handles_changes_payload_with_new_status(self):
        event = {
            "action": "update",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Restore DB snapshot from production in local",
        )

    def test_handles_updated_from_status_marker(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Restore DB snapshot from production in local",
        )

    def test_matches_status_case_and_separator_variants(self):
        for status in ("To Research", "to_research", "TO-RESEARCH", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "statusChanged",
                        "newStatus": status,
                        "id": "POI-4560",
                        "title": "Investigate production data",
                    }
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_uses_status_field_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4560",
                "title": "Investigate production data",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_status_field_for_generic_linear_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4560",
                    "title": "Restore DB snapshot from production in local",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "cursor researching: Restore DB snapshot from production in local",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "  Investigate production data  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_skips_missing_required_issue_fields(self):
        base_context = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4560",
            "title": "Investigate production data",
        }
        for field in ("id", "title"):
            with self.subTest(field=field):
                context = dict(base_context)
                context.pop(field)

                self.assertIsNone(build_issue_title_update({"triggerContext": context}))

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))

    def test_cli_outputs_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            },
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
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )


if __name__ == "__main__":
    unittest.main()
