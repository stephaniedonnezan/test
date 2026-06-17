import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5032",
                "title": (
                    "Direct connection PPA are not added to the PPA in the "
                    "mass balance export"
                ),
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5032",
                "title": (
                    "Cursor researching: Direct connection PPA are not added "
                    "to the PPA in the mass balance export"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5032",
                "title": "Direct connection PPA are not reflected correctly",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5032",
                "title": "Direct connection PPA are not reflected correctly",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5032",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5032",
                    "title": "Direct connection PPA missing in mass balance export",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5032",
                "title": (
                    "Cursor researching: Direct connection PPA missing in "
                    "mass balance export"
                ),
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5032",
                    "title": "Direct connection PPA missing in mass balance export",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_change_object_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": "toResearch"}},
            "data": {
                "issue": {
                    "identifier": "POI-5032",
                    "title": "Direct connection PPA missing in mass balance export",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5032",
                "title": (
                    "Cursor researching: Direct connection PPA missing in "
                    "mass balance export"
                ),
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5032",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
