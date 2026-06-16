import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4878",
                "title": "Cursor researching: LPH enablement even if no BOP",
            },
        )

    def test_accepts_whole_cursor_automation_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "TO_RESEARCH",
                "id": "POI-4878",
                "title": "LPH enablement even if no BOP",
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: LPH enablement even if no BOP")

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4878",
            "title": "cursor researching: LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "title": "Investigate LPH allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate LPH allocation",
            },
        )

    def test_accepts_changed_status_to_value(self):
        event = {
            "action": "update",
            "changes": {"status": {"from": "Backlog", "to": "to-research"}},
            "data": {
                "identifier": "POI-4878",
                "title": "Investigate LPH allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate LPH allocation",
        )

    def test_ignores_issue_updates_without_status_change_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4878",
                "title": "LPH enablement even if no BOP",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4878",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
