import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_title_for_trigger_context_status_changed_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4631",
                "title": "An external input could be added as RFNBO even if the POS is not there",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4631",
                "title": (
                    "Cursor researching: An external input could be added as RFNBO even if the POS "
                    "is not there"
                ),
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

    def test_updates_title_for_nested_issue_payload(self):
        event = {
            "webhookType": "status changed",
            "newStatus": "to-research",
            "issue": {
                "id": "POI-1",
                "title": "Nested issue title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_updates_title_when_status_is_nested_in_state(self):
        event = {
            "webhookType": "status changed",
            "issueId": "POI-2",
            "title": "State based payload",
            "state": {"name": "toResearch"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: State based payload",
            },
        )

    def test_falls_back_to_identifier_when_id_is_absent(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-3",
            "title": "Identifier based payload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Identifier based payload",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_does_not_update_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4631",
            "title": "An external input could be added as RFNBO even if the POS is not there",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4631",
            "title": "An external input could be added as RFNBO even if the POS is not there",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4631",
            "title": "cursor researching: An external input could be added as RFNBO",
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
                    "id": "POI-4631",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
