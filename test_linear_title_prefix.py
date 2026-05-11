import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3605",
                "title": "Mass balance representation for large volumes",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3605",
                "title": "Cursor researching: Mass balance representation for large volumes",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Check the flow",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Check the flow",
        )

    def test_uses_nested_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Review delivery origin",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Review delivery origin",
            },
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Search options",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_statuses_other_than_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3605",
                "title": "Mass balance representation for large volumes",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_cursor_researching_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5",
                }
            )
        )

    def test_exposes_compatibility_alias(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "Alias entrypoint",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
