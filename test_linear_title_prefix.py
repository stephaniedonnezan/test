import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_cursor_trigger_context_to_research_updates_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4579",
                "title": "MB export corrections",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_automation_trigger_info_wrapper_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Wrapped payload",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Wrapped payload",
            },
        )

    def test_camel_case_status_change_and_status_are_normalized(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-124",
                "title": "Camel case payload",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case payload",
        )

    def test_hyphenated_and_underscored_status_values_match(self):
        for status in ("to-research", "to_research", "To   Research"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-125",
                        "title": "Flexible status",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Flexible status",
                )

    def test_non_research_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4579",
                "title": "MB export corrections",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4579",
                "title": "MB export corrections",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4579",
                "title": "cursor researching: MB export corrections",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_title_and_identifier_are_trimmed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4579 ",
                "title": "  MB export corrections  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_missing_issue_identity_is_ignored(self):
        event = {"triggerContext": {"trigger": "status_changed", "newStatus": "To Research"}}

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))

    def test_native_linear_update_with_updated_fields_uses_data_issue(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-126",
                    "title": "Native nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-126",
                "title": "Cursor researching: Native nested issue",
            },
        )

    def test_native_linear_update_with_changes_uses_new_status_value(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {"id": "POI-127", "title": "Changed status"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status",
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-128",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_explicit_new_status_takes_precedence_over_nested_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-129",
                "title": "Completed issue",
                "state": {"name": "To Research"},
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handler_alias_matches_primary_function(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "identifier": "POI-130",
                "title": "Alias payload",
            }
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-131",
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
                "issueId": "POI-131",
                "title": f"{TITLE_PREFIX}: CLI payload",
            },
        )

    def test_cli_is_silent_for_non_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-132",
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

        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
