import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_automation_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4639",
                "title": "Methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_uses_status_field_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "to research",
            "issue_id": "POI-1",
            "title": "Hydrogen",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Hydrogen",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Ammonia",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Ammonia",
            },
        )

    def test_accepts_workflow_state_name(self):
        event = {
            "action": "status-change",
            "issue": {
                "id": "POI-3",
                "title": "Synthetic fuel",
                "workflowState": {"name": "ToResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Synthetic fuel",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4",
                "title": "Methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "Methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "cursor researching: Methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identity_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "No ID",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
