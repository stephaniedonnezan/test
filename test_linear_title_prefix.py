import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_updates_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4880",
            "title": "BUG: Site Management reloads when switching month",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4880",
                "title": "Cursor researching: BUG: Site Management reloads when switching month",
            },
        )

    def test_cloud_automation_trigger_context_wrapper_updates_title(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4880",
                    "title": "BUG: Site Management reloads when switching month",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4880",
                "title": "Cursor researching: BUG: Site Management reloads when switching month",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4880",
            "title": "BUG: Site Management reloads when switching month",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4880",
            "title": "BUG: Site Management reloads when switching month",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4880",
            "title": "cursor researching: BUG: Site Management reloads when switching month",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "trigger": "Status Changed",
            "new_status": "to_research",
            "issue_id": "POI-4880",
            "title": "Switching periods reloads Site Management",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Switching periods reloads Site Management",
        )

    def test_nested_linear_update_with_state_marker_updates_title(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4880",
                "title": "Switching periods reloads Site Management",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4880",
                "title": "Cursor researching: Switching periods reloads Site Management",
            },
        )

    def test_generic_update_requires_status_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4880",
                "title": "Switching periods reloads Site Management",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_payload_supplies_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "identifier": "POI-4880",
                "title": "Switching periods reloads Site Management",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Switching periods reloads Site Management",
        )

    def test_updated_from_state_id_marks_linear_state_update(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "previous-state-id"},
            "data": {
                "identifier": "POI-4880",
                "title": "Switching periods reloads Site Management",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4880")

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4880 ",
            "title": "  Switching periods reloads Site Management  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4880",
                "title": "Cursor researching: Switching periods reloads Site Management",
            },
        )

    def test_missing_issue_id_returns_none(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Switching periods reloads Site Management",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_returns_none(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4880",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_returns_none(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
