import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_payload_prefixes_title(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_automation_trigger_context_payload_prefixes_title(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "automation_trigger_info": {
                        "triggerContext": {
                            "trigger": "status_changed",
                            "newStatus": "to research",
                            "id": "POI-5058",
                            "title": "Move the mb-data-manager into the psqo module",
                        }
                    }
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_case_and_separator_variants_are_normalized(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "new_status": "TO_RESEARCH",
                    "issueId": "POI-1",
                    "title": "Investigate production output",
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate production output",
            },
        )

    def test_ignores_other_target_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "In Review",
                    "id": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                }
            )
        )

    def test_ignores_non_status_change_triggers(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                }
            )
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5058",
                    "title": "cursor researching: Move the mb-data-manager into the psqo module",
                }
            )
        )

    def test_nested_linear_update_with_status_field_prefixes_title(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "action": "update",
                    "type": "Issue",
                    "updatedFields": ["state"],
                    "data": {
                        "id": "webhook-event-id",
                        "issue": {
                            "identifier": "POI-5058",
                            "title": "Move the mb-data-manager into the psqo module",
                            "state": {"name": "To Research"},
                        },
                    },
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_nested_linear_change_object_uses_new_status_value(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "webhookType": "Issue Updated",
                    "changes": {"status": {"old": "Backlog", "new": "To Research"}},
                    "issue": {
                        "key": "POI-2",
                        "title": "Research assisted database output lookup",
                    },
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research assisted database output lookup",
            },
        )

    def test_generic_update_without_status_metadata_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["description"],
                    "data": {
                        "issue": {
                            "identifier": "POI-5058",
                            "title": "Move the mb-data-manager into the psqo module",
                            "state": {"name": "To Research"},
                        }
                    },
                }
            )
        )

    def test_missing_required_issue_fields_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5058",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )


if __name__ == "__main__":
    unittest.main()
