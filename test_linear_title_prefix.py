import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handleIssueStatusChanged,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_automation_payload_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4606",
                "title": "QA 1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4606",
                "title": "Cursor researching: QA 1",
            },
        )

    def test_accepts_direct_flat_payload(self):
        event = {
            "trigger": "statusChanged",
            "status": "to research",
            "issueId": "POI-123",
            "title": "Investigate methane export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate methane export",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4606",
            "title": "QA 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4606",
            "title": "QA 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4606",
            "title": "cursor researching: QA 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_case_separators_and_camel_case(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "identifier": "POI-4606",
            "title": "QA 1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4606",
                "title": "Cursor researching: QA 1",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-4606",
                    "title": "QA 1",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4606",
                "title": "Cursor researching: QA 1",
            },
        )

    def test_ignores_nested_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "POI-4606",
                    "title": "QA 1",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_explicit_new_status_wins_over_current_status_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "status": "Done",
                "id": "POI-4606",
                "title": "QA 1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4606",
                "title": "Cursor researching: QA 1",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": "To Research",
            "issue_id": " POI-4606 ",
            "title": "  QA 1  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4606",
                "title": "Cursor researching: QA 1",
            },
        )

    def test_returns_none_for_incomplete_or_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))

    def test_compatibility_wrappers_delegate_to_builder(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4606",
            "title": "QA 1",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))
        self.assertEqual(handleIssueStatusChanged(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
