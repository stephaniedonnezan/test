import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4895",
                "title": "improve cascade rules for the psqo entity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-123",
            "title": "Review Linear automation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review Linear automation",
            },
        )

    def test_supports_nested_linear_issue_updated_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Add research prefix",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Add research prefix",
            },
        )

    def test_prefers_change_destination_for_generic_update_payloads(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "id": "internal-id",
                    "identifier": "POI-789",
                    "title": "Investigate flaky trigger",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Investigate flaky trigger",
            },
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4895",
                "title": "improve cascade rules for the psqo entity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_research_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4895",
                "title": "improve cascade rules for the psqo entity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4895",
            "title": "cursor researching: improve cascade rules for the psqo entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No ID"}
            )
        )

    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4895",
                "title": "improve cascade rules for the psqo entity",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4895",
                "title": "Cursor researching: improve cascade rules for the psqo entity",
            },
        )


if __name__ == "__main__":
    unittest.main()
