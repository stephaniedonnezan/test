import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_automation_status_change_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4042",
                    "title": "Solve the flake",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4042",
                "title": "Cursor researching: Solve the flake",
            },
        )

    def test_accepts_direct_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-1",
            "title": "Investigate settlement",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate settlement",
            },
        )

    def test_accepts_status_variants(self):
        event = {
            "trigger": "status_changed",
            "new_status": "toResearch",
            "identifier": "POI-2",
            "title": "Check flaky test",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check flaky test",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to-research",
            "key": "POI-3",
            "title": "Look at webhook payload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Look at webhook payload",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_change_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_accepts_changes_mapping_as_status_change_marker(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "identifier": "POI-5",
                "title": "Changes object",
                "workflowState": {"name": "to_research"},
            },
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Changes object",
            },
        )

    def test_ignores_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-6",
            "title": "Completed item",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-8",
                "title": "Renamed issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
