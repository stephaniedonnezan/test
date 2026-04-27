import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4340",
                "title": "Prevent delivery edits",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4340",
                "title": "Cursor researching: Prevent delivery edits",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status changed",
            "newStatus": "to-research",
            "issueId": "POI-1",
            "title": "Investigate thing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate thing",
            },
        )

    def test_uses_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS_CHANGED",
                "status": "to research",
                "id": "POI-2",
                "title": "Investigate status fallback",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate status fallback",
        )

    def test_returns_none_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4340",
                "title": "Prevent delivery edits",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4340",
                "title": "Prevent delivery edits",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4340",
                "title": "Cursor researching: Prevent delivery edits",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4340",
                "title": "cursor researching - Prevent delivery edits",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_issue_id_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Prevent delivery edits",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4340",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
