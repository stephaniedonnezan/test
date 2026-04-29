import unittest

from linear_title_prefix import PREFIX, build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "[]Finalise MB export revamp",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": f"{PREFIX}: []Finalise MB export revamp",
            },
        )

    def test_accepts_nested_linear_payload_shape(self):
        event = {
            "type": "Issue",
            "action": "statusChanged",
            "data": {
                "id": "issue-123",
                "title": "Research export calculations",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": f"{PREFIX}: Research export calculations",
            },
        )

    def test_accepts_issue_id_when_id_is_absent(self):
        event = {
            "trigger": "status changed",
            "status": "to_research",
            "issueId": "POI-4579",
            "title": "Finalise MB export revamp",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4579",
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "Finalise MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4579",
            "title": "Finalise MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_status_when_new_status_is_missing(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-4579",
            "title": "Finalise MB export revamp",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{PREFIX}: Finalise MB export revamp",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "Cursor researching: Finalise MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "cursor researching - Finalise MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "  Finalise MB export revamp  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{PREFIX}: Finalise MB export revamp",
        )

    def test_ignores_events_without_issue_identity(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Finalise MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_events_without_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4579",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
