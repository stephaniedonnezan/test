import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3815",
                "title": "Improve amount transported calculation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3815",
                "title": "Cursor researching: Improve amount transported calculation",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "To Research",
            "issueId": "POI-100",
            "title": "Review customer CSV import",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Review customer CSV import",
            },
        )

    def test_accepts_linear_issue_payload_with_action(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "data": {
                "id": "POI-101",
                "title": "Add container transport formula",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Add container transport formula",
            },
        )

    def test_accepts_issue_nested_under_data(self):
        event = {
            "trigger": "status-changed",
            "data": {
                "issue": {
                    "identifier": "POI-102",
                    "title": "Calculate shipment weight",
                    "new_status": "to_research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-102",
                "title": "Cursor researching: Calculate shipment weight",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-3815",
            "title": "Improve amount transported calculation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3815",
            "title": "Improve amount transported calculation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3815",
            "title": "cursor researching: Improve amount transported calculation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3815",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
