import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_status_changed_to_research_updates_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5104",
                "title": "Cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
            },
        )

    def test_nested_cursor_trigger_context_updates_title(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5104",
                    "title": "Phase 3: Frontend - POS extraction UI adaptations",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5104",
                "title": "Cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
            },
        )

    def test_current_in_review_trigger_does_not_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_does_not_update(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_linear_update_with_nested_issue_state_updates_title(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5104",
                    "title": "Phase 3: Frontend - POS extraction UI adaptations",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5104",
                "title": "Cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
            },
        )

    def test_changes_payload_can_supply_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"old": "Todo", "new": "To Research"}},
            "issueId": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
        )

    def test_status_normalization_accepts_camelcase_and_separators(self):
        statuses = ["toResearch", "to_research", "to-research", "TO RESEARCH"]

        for status in statuses:
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-5104",
                    "title": "Phase 3: Frontend - POS extraction UI adaptations",
                }
                self.assertIsNotNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5104",
            "title": "cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_issue_id_and_title_are_trimmed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-5104 ",
            "title": " Phase 3: Frontend - POS extraction UI adaptations ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5104",
                "title": "Cursor researching: Phase 3: Frontend - POS extraction UI adaptations",
            },
        )

    def test_missing_issue_id_or_title_does_not_update(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No ID"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5104"}
            )
        )

    def test_wrapper_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_emits_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5104",
            "title": "Phase 3: Frontend - POS extraction UI adaptations",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(json.loads(result.stdout)["action"], "update_issue_title")


if __name__ == "__main__":
    unittest.main()
