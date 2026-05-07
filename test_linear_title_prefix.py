import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_title_for_trigger_context_status_changed_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4487",
                "title": "Give an auditor access to 2 audits",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4487",
                "title": "Cursor researching: Give an auditor access to 2 audits",
            },
        )

    def test_updates_title_for_nested_linear_data_issue(self):
        event = {
            "action": "statusChanged",
            "data": {
                "new_status": "to_research",
                "issue": {
                    "id": "issue-id",
                    "title": "Investigate certificate date",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate certificate date",
            },
        )

    def test_updates_title_for_issue_payload(self):
        event = {
            "type": "status-changed",
            "status": "to research",
            "issue": {
                "issueId": "POI-123",
                "name": "Nested issue title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_updates_title_when_status_is_nested_in_state(self):
        event = {
            "webhookType": "status changed",
            "issueId": "POI-1",
            "title": "State based payload",
            "state": {"name": "to-research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: State based payload",
            },
        )

    def test_accepts_identifier_when_id_is_absent(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-456",
            "title": "Identifier payload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Identifier payload",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-789 ",
            "title": "  Trim this title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Trim this title",
            },
        )

    def test_does_not_update_for_done_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4487",
            "title": "Give an auditor access to 2 audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4487",
            "title": "Give an auditor access to 2 audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4487",
            "title": "cursor researching: Give an auditor access to 2 audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4487",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
