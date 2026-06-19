import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing, show discrepancies in batches",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing, show discrepancies in batches",
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "ToResearch",
                    "id": "POI-4421",
                    "title": "Spreadsheet testing",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "cursor researching: Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_status_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4421",
                    "title": "Spreadsheet testing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4421",
                    "title": "Spreadsheet testing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_workflow_state_name(self):
        event = {
            "webhookType": "Issue Updated",
            "changedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4421",
                    "title": "Spreadsheet testing",
                    "workflowState": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": " POI-4421 ",
            "title": " Spreadsheet testing ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing",
            },
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
