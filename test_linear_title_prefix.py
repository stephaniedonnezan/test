import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_flat_status_changed_event_for_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4475",
                    "title": "Custom LHV for methane plant for turn2x",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4475",
                "title": f"{TITLE_PREFIX}: Custom LHV for methane plant for turn2x",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-1",
                "title": "Investigate electrolyzer feedstock",
            }
        )

        self.assertEqual(result["title"], f"{TITLE_PREFIX}: Investigate electrolyzer feedstock")

    def test_uses_status_fallback_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "status": "to-research",
                "id": "POI-2",
                "title": "Research methane conversion",
            }
        )

        self.assertEqual(result["issueId"], "POI-2")

    def test_updates_nested_linear_issue_update_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "type": "Issue",
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-3",
                    "title": "Handle custom methane LHV",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": f"{TITLE_PREFIX}: Handle custom methane LHV",
            },
        )

    def test_updates_when_updated_from_contains_status_field(self):
        result = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFrom": {"workflowState": "Backlog"},
                "data": {
                    "id": "POI-4",
                    "title": "Review workflow state name",
                    "workflowState": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], f"{TITLE_PREFIX}: Review workflow state name")

    def test_updates_when_linear_updated_from_contains_state_id(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFrom": {"stateId": "old-state-id"},
                "data": {
                    "id": "POI-12",
                    "title": "Support Linear state id diffs",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], f"{TITLE_PREFIX}: Support Linear state id diffs")

    def test_accepts_status_name_mapping(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": {"name": "To Research"},
                "id": "POI-13",
                "title": "Status name object",
            }
        )

        self.assertEqual(result["title"], f"{TITLE_PREFIX}: Status name object")

    def test_returns_none_for_non_target_status(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "In Progress",
                    "id": "POI-5",
                    "title": "Already ready for implementation",
                }
            )
        )

    def test_returns_none_for_non_status_trigger(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-6",
                    "title": "Comment should not change title",
                }
            )
        )

    def test_returns_none_for_issue_update_without_status_field_change(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["title"],
                    "data": {
                        "id": "POI-7",
                        "title": "Only the title changed",
                        "state": {"name": "To Research"},
                    },
                }
            )
        )

    def test_returns_none_when_title_already_has_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-8",
                    "title": "cursor researching: Existing title",
                }
            )
        )

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-9"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No id"}
            )
        )

    def test_compatibility_wrapper_matches_primary_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
            "title": "Wrapper support",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-11",
            "title": "CLI support",
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
                "issueId": "POI-11",
                "title": f"{TITLE_PREFIX}: CLI support",
            },
        )


if __name__ == "__main__":
    unittest.main()
