import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4539",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4539",
                "title": "Cursor researching: Column sizing in all tables in Atmen",
            },
        )

    def test_accepts_flat_event_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4539",
            "title": "Column sizing in all tables in Atmen",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4539",
                "title": "Cursor researching: Column sizing in all tables in Atmen",
            },
        )

    def test_accepts_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "To_Research",
                "id": "POI-4539",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4539",
                "title": "Cursor researching: Column sizing in all tables in Atmen",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4539",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4539",
                "title": "Cursor researching: Column sizing in all tables in Atmen",
            },
        )

    def test_does_not_prefix_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4539",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_prefix_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4539",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4539",
                "title": "Cursor researching: Column sizing in all tables in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4539",
                "title": "cursor researching - Column sizing in all tables in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Column sizing in all tables in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4539",
                "title": " ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
