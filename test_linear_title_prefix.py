import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4736",
                "title": "Scaffold delivery transport emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4736",
                "title": "Cursor researching: Scaffold delivery transport emissions",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4736",
                "title": "Scaffold delivery transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4736",
                "title": "Scaffold delivery transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4736",
                "title": "cursor researching: Scaffold delivery transport emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4736",
                "title": "cursor researching: Scaffold delivery transport emissions",
            },
        )

    def test_normalizes_status_trigger_and_status_name(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-4736",
                "title": "Scaffold delivery transport emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Scaffold delivery transport emissions",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "id": "webhook-event-id",
            "data": {
                "updatedFields": ["state"],
                "changes": {
                    "state": {
                        "oldValue": {"name": "Todo"},
                        "newValue": {"name": "To Research"},
                    }
                },
                "issue": {
                    "id": "linear-internal-id",
                    "identifier": "POI-4736",
                    "title": "Scaffold delivery transport emissions",
                    "state": {"name": "Todo"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4736",
                "title": "Cursor researching: Scaffold delivery transport emissions",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4736",
                    "title": "Scaffold delivery transport emissions",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_workflow_state_name_when_no_explicit_status(self):
        event = {
            "triggerContext": {
                "webhookType": "state_change",
                "workflowState": {"name": "to_research"},
                "identifier": "POI-4736",
                "title": "Scaffold delivery transport emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Scaffold delivery transport emissions",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "new_status": " to research ",
                "id": " POI-4736 ",
                "title": " Scaffold delivery transport emissions ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4736",
                "title": "Cursor researching: Scaffold delivery transport emissions",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4736",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
