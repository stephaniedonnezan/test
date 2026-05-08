import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4627",
                "title": "Cursor researching: Initialisation error",
            },
        )

    def test_supports_cursor_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4627",
                "title": "Initialisation error",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Initialisation error",
        )

    def test_supports_nested_issue_data_with_outer_status_metadata(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
            },
            "data": {
                "issue": {
                    "identifier": "POI-4627",
                    "title": "Initialisation error",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4627",
                "title": "Cursor researching: Initialisation error",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4627",
            "title": "cursor researching: Initialisation error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_common_target_status_spellings(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "id": "POI-4627",
                    "title": "Initialisation error",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Initialisation error",
                )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "issueId": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4627")

    def test_reads_state_name_when_status_is_nested(self):
        event = {
            "trigger": "state_changed",
            "state": {"name": "to research"},
            "issue_id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4627")

    def test_accepts_issue_updated_event_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["priority", "status"],
            "newStatus": "to research",
            "id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Initialisation error",
        )

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["priority"],
            "newStatus": "to research",
            "id": "POI-4627",
            "title": "Initialisation error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_valid_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4627",
                    "title": " ",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
