import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3875",
                "title": "Missing green electricity error message is missleading",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3875",
                "title": "Cursor researching: Missing green electricity error message is missleading",
            },
        )

    def test_accepts_status_changed_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "ToResearch",
            "issueId": "POI-100",
            "title": "Investigate allocation page",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Investigate allocation page",
            },
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-101",
            "title": "Research issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-102",
                "title": "Research issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-103",
            "title": "cursor researching: Research issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-103",
                "title": "cursor researching: Research issue",
            },
        )

    def test_accepts_generic_update_when_updated_fields_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-104",
                    "title": "Scope research",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-104",
                "title": "Cursor researching: Scope research",
            },
        )

    def test_accepts_changed_status_to_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "issue": {
                "key": "POI-105",
                "title": "Validate Linear payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-105",
                "title": "Cursor researching: Validate Linear payload",
            },
        )

    def test_prefers_identifier_over_raw_linear_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "3f56a1ef-7083-4e1a-9476-0d4eebc02610",
                    "identifier": "POI-106",
                    "title": "Use human readable identifier",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-106",
        )

    def test_trims_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-107",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trim me",
        )

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing identifier",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-108",
                }
            )
        )

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
