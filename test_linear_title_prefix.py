import unittest

from linear_title_prefix import (
    build_issue_title_update,
    should_prefix_issue_title,
    with_researching_prefix,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_when_issue_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3823",
                "title": "Closing the MB refinement",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3823",
                "title": "Cursor researching: Closing the MB refinement",
            },
        )

    def test_accepts_flat_event_shape(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-1",
            "title": "Investigate flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate flow",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-2",
                "title": "Fallback status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Fallback status",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "To_Research",
                "id": "POI-3",
                "title": "Mixed formatting",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Mixed formatting",
        )

    def test_noops_for_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "Wrong trigger",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_noops_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-5",
                "title": "Wrong status",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_noops_when_title_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "Cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        self.assertFalse(
            should_prefix_issue_title("cursor RESEARCHING: Existing title")
        )

    def test_noops_without_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_noops_without_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_title(self):
        self.assertEqual(
            with_researching_prefix("Investigate issue"),
            "Cursor researching: Investigate issue",
        )


if __name__ == "__main__":
    unittest.main()
