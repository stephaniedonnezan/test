import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_title_for_trigger_context_status_change_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4643",
                "title": "Title in Edit page from Production says Trading",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4643",
                "title": "Cursor researching: Title in Edit page from Production says Trading",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4643",
                "title": "Title in Edit page from Production says Trading",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4643",
                "title": "Title in Edit page from Production says Trading",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_linear_action_and_nested_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4643",
                    "title": "Title in Edit page from Production says Trading",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4643",
                "title": "Cursor researching: Title in Edit page from Production says Trading",
            },
        )

    def test_accepts_flat_snake_case_payload(self):
        event = {
            "trigger": "status changed",
            "new_status": "to_research",
            "issue_id": "POI-4643",
            "title": "Title in Edit page from Production says Trading",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4643",
                "title": "Cursor researching: Title in Edit page from Production says Trading",
            },
        )

    def test_accepts_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4643",
            "title": "Title in Edit page from Production says Trading",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4643",
                "title": "Cursor researching: Title in Edit page from Production says Trading",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4643",
                "title": "cursor researching: Title in Edit page from Production says Trading",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4643",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Title in Edit page from Production says Trading",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
