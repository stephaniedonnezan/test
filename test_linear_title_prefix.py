import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_automation_status_changes_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4100",
                "title": '[]Update the "Metered readings " page',
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4100",
                "title": 'Cursor researching: []Update the "Metered readings " page',
            },
        )

    def test_accepts_flat_automation_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4100",
            "title": "Issue Atmen Prod",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Issue Atmen Prod",
        )

    def test_accepts_nested_linear_data_payload(self):
        event = {
            "type": "Issue",
            "action": "statusChanged",
            "data": {
                "id": "issue-uuid",
                "title": "Investigate allocations",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate allocations",
            },
        )

    def test_accepts_issue_object_payload(self):
        event = {
            "trigger": "status changed",
            "issue": {
                "issueId": "POI-4100",
                "title": "Investigate allocations",
                "status": "to_research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate allocations",
        )

    def test_accepts_outer_trigger_with_nested_issue_details(self):
        event = {
            "trigger": "status_changed",
            "issue": {
                "issueId": "POI-4100",
                "title": "Investigate allocations",
                "status": "to research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate allocations",
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "trigger": "status_changed",
            "status": "to-research",
            "issueId": "POI-4100",
            "title": "Investigate allocations",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate allocations",
        )

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "action": "statusChanged",
            "state": "toResearch",
            "id": "POI-4100",
            "title": "Investigate allocations",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate allocations",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "  POI-4100  ",
            "title": "  Issue Atmen Prod  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4100",
                "title": "Cursor researching: Issue Atmen Prod",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4100",
            "title": "Issue Atmen Prod",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4100",
            "title": "Issue Atmen Prod",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4100",
            "title": "cursor researching: Issue Atmen Prod",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Issue Atmen Prod",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4100",
            "title": "  ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
