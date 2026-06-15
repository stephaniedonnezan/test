import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4932",
                "title": "Improve stored file transaction delegate",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4932",
                "title": "Improve stored file transaction delegate",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4932",
                "title": "Improve stored file transaction delegate",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4932",
                "title": "cursor researching: Improve stored file transaction delegate",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4932",
                "title": "Improve stored file transaction delegate",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4932",
                    "title": "Improve stored file transaction delegate",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_handles_changes_new_value_for_generic_update(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "changes": {
                    "status": {
                        "from": {"name": "Todo"},
                        "to": {"name": "To Research"},
                    }
                },
                "issue": {
                    "id": "POI-4932",
                    "title": "Improve stored file transaction delegate",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_ignores_generic_update_without_status_change_marker(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "id": "POI-4932",
                    "title": "Improve stored file transaction delegate",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title_before_building_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": " POI-4932 ",
                "title": " Improve stored file transaction delegate ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve stored file transaction delegate",
            },
        )

    def test_ignores_payloads_missing_required_issue_data(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4932",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
