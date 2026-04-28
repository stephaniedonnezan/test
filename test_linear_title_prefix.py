import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4491",
                "title": "Cursor researching: N+1 Query",
            },
        )

    def test_accepts_flat_payloads_and_issue_id_alias(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "issueId": "POI-4491",
            "title": "N+1 Query",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4491",
                "title": "Cursor researching: N+1 Query",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: N+1 Query",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "cursor researching: N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "  N+1 Query  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: N+1 Query",
        )

    def test_requires_issue_id_and_title(self):
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
            }
        }
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_title))
        self.assertIsNone(build_issue_title_update(missing_id))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
