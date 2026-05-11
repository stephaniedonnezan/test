import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4645",
                "title": "Cursor researching: Logger.errorWithTags",
            },
        )

    def test_accepts_current_linear_trigger_context_shape(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4645",
                "title": "Logger.errorWithTags",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4645",
                "title": "Cursor researching: Logger.errorWithTags",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4645",
                "title": "Logger.errorWithTags",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4645",
                "title": "Cursor researching: Logger.errorWithTags",
            },
        )

    def test_accepts_camel_case_status(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Logger.errorWithTags",
        )

    def test_webhook_type_issue_does_not_mask_status_changed_action(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Logger.errorWithTags",
        )

    def test_uses_state_name_when_status_is_nested(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Logger.errorWithTags",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4645",
            "title": "Logger.errorWithTags",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4645",
            "title": "cursor researching: Logger.errorWithTags",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4645"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
