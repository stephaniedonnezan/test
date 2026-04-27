import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]batch POS export per offtaker",
                "id": "POI-4316",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4316",
                "title": "Cursor researching: []batch POS export per offtaker",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Investigate POS export",
                "id": "POI-4316",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "title": "Investigate POS export",
                "id": "POI-4316",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "status": "To_Research",
                "title": "Investigate POS export",
                "id": "POI-4316",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4316",
                "title": "Cursor researching: Investigate POS export",
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "Status Changed",
            "newStatus": "TO RESEARCH",
            "title": "Investigate POS export",
            "issueId": "POI-4316",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4316",
                "title": "Cursor researching: Investigate POS export",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "cursor researching: Investigate POS export",
                "id": "POI-4316",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        base_event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate POS export",
                "id": "POI-4316",
            }
        }

        missing_title = {"triggerContext": {**base_event["triggerContext"], "title": ""}}
        missing_id = {"triggerContext": {**base_event["triggerContext"], "id": ""}}

        self.assertIsNone(build_issue_title_update(missing_title))
        self.assertIsNone(build_issue_title_update(missing_id))


if __name__ == "__main__":
    unittest.main()
