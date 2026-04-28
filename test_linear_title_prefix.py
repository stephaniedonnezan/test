import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            },
        )

    def test_accepts_flat_event_payload(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "id": "POI-4572",
            "title": "Trader Mass Balance Export Issues",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "issueId": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "cursor researching Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "  Trader Mass Balance Export Issues  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trader Mass Balance Export Issues",
        )

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not an event"))


if __name__ == "__main__":
    unittest.main()
