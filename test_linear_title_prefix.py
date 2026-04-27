import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4476",
                "title": "PPA consumption decimal error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4476",
                "title": "Cursor researching: PPA consumption decimal error",
            },
        )

    def test_returns_none_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4476",
                "title": "PPA consumption decimal error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4476",
                "title": "PPA consumption decimal error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4476",
                "title": "Cursor researching: PPA consumption decimal error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4476",
                "title": "cursor RESEARCHING - PPA consumption decimal error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_flat_event_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4476",
            "title": "PPA consumption decimal error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4476",
                "title": "Cursor researching: PPA consumption decimal error",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4476",
                "title": "PPA consumption decimal error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4476",
                "title": "Cursor researching: PPA consumption decimal error",
            },
        )

    def test_normalizes_separator_and_casing_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": " TO_RESEARCH ",
                "id": "POI-4476",
                "title": "PPA consumption decimal error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4476",
                "title": "Cursor researching: PPA consumption decimal error",
            },
        )

    def test_returns_none_when_required_fields_are_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "to research"}}
            )
        )


if __name__ == "__main__":
    unittest.main()
