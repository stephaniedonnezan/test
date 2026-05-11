import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2930",
            "title": "Address Turn2X Non Conformities",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2930",
                "title": "Cursor researching: Address Turn2X Non Conformities",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2930",
                "title": "Address Turn2X Non Conformities",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Address Turn2X Non Conformities",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-2930",
            "title": "Address Turn2X Non Conformities",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-2930",
            "title": "Address Turn2X Non Conformities",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-2930",
            "title": "cursor researching: Address Turn2X Non Conformities",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_research_status_spelling(self):
        event = {
            "trigger": "status changed",
            "new_status": "ToResearch",
            "issue_id": "POI-2930",
            "title": "Address Turn2X Non Conformities",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Address Turn2X Non Conformities",
        )

    def test_accepts_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "id": "issue-id",
                "identifier": "POI-2930",
                "title": "Address Turn2X Non Conformities",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Address Turn2X Non Conformities",
            },
        )

    def test_ignores_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-2930",
                "title": "Address Turn2X Non Conformities",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2930",
            "state": {"name": "To Research"},
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
