import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4564",
                "title": "Cursor researching: Inputs were set to 0",
            },
        )

    def test_accepts_flat_payloads_and_status_fallback(self):
        event = {
            "trigger": "status-changed",
            "status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export",
            },
        )

    def test_prefers_nested_trigger_context_values(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "OUTER",
            "title": "Outer title",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "INNER",
                "title": "Inner title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "INNER",
                "title": "Cursor researching: Inner title",
            },
        )

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "Investigate export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_statuses_other_than_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-1",
            "title": "Investigate export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "cursor researching: Investigate export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Investigate export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "  Investigate export  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export",
            },
        )

    def test_handles_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
