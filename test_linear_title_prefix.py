import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4489",
                "title": "2026-04-18-DailyReport",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4489",
                "title": "Cursor researching: 2026-04-18-DailyReport",
            },
        )

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4489",
                "title": "Needs research",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4489",
                "title": "Needs research",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4489",
                "title": "Needs research",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4489",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_accepts_nested_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "new_status": "to_research",
                "issue": {
                    "identifier": "POI-4489",
                    "title": "Needs research",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4489",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_accepts_state_name_fallback(self):
        event = {
            "trigger": "status changed",
            "state": {"name": "TO-RESEARCH"},
            "issueId": "issue-123",
            "title": "Needs research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_metadata(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4489",
                "title": "Outer title",
                "issue": {"id": "wrong", "title": "Nested title"},
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4489",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4489",
                "title": "cursor researching: Needs research",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4489",
                "title": "  Needs research  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4489",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Needs research",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4489",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
