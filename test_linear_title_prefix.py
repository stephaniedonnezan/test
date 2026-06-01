import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4500",
                "title": "Implement Certifhy chip in audit",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4500",
                "title": "Cursor researching: Implement Certifhy chip in audit",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4500",
            "title": "Implement Certifhy chip in audit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4500",
            "title": "Implement Certifhy chip in audit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4500",
            "title": "cursor researching: Implement Certifhy chip in audit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4500",
                "title": "Implement Certifhy chip in audit",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Implement Certifhy chip in audit",
            },
        )

    def test_accepts_status_format_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "identifier": "POI-4500",
            "title": "Implement Certifhy chip in audit",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4500",
                "title": "Cursor researching: Implement Certifhy chip in audit",
            },
        )

    def test_ignores_linear_update_for_non_status_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Implement Certifhy chip in audit",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
