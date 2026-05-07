import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2787",
                "title": "3. Alerts on MB",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2787",
                "title": "Cursor researching: 3. Alerts on MB",
            },
        )

    def test_accepts_status_name_with_different_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-2787",
            "title": "Alerts on MB",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2787",
                "title": "Cursor researching: Alerts on MB",
            },
        )

    def test_uses_status_when_new_status_is_not_present(self):
        event = {
            "trigger": "status_changed",
            "status": "to-research",
            "identifier": "POI-2787",
            "title": "Alerts on MB",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2787",
                "title": "Cursor researching: Alerts on MB",
            },
        )

    def test_accepts_linear_issue_updated_event_when_status_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "state": {"name": "To Research"},
            "issue": {
                "id": "issue-id",
                "title": "Needs investigation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Needs investigation",
            },
        )

    def test_returns_none_for_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-2787",
            "title": "3. Alerts on MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-2787",
            "title": "3. Alerts on MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_issue_updated_event_did_not_change_status(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-2787",
            "title": "3. Alerts on MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2787",
            "title": "cursor researching: 3. Alerts on MB",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "3. Alerts on MB",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-2787",
                }
            )
        )

    def test_returns_none_for_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a mapping"))


if __name__ == "__main__":
    unittest.main()
