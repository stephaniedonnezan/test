import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3980",
                "title": (
                    "Cursor researching: "
                    "Bug: Inconsistent units for yearly amount and supplier list"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_events(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_already_prefixed_titles(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-3980",
                    "title": (
                        "cursor researching: "
                        "Bug: Inconsistent units for yearly amount and supplier list"
                    ),
                }
            }
        )

        self.assertIsNone(result)

    def test_normalizes_status_separators_and_camel_case(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "toResearch",
                    "id": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                }
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: "
            "Bug: Inconsistent units for yearly amount and supplier list",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "id": "issue-id",
                    "identifier": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": (
                    "Cursor researching: "
                    "Bug: Inconsistent units for yearly amount and supplier list"
                ),
            },
        )

    def test_handles_linear_updated_from_state_id_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFrom": {"stateId": "old-state-id"},
                "data": {
                    "identifier": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                    "workflowState": {"name": "to_research"},
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-3980")
        self.assertEqual(
            result["title"],
            "Cursor researching: "
            "Bug: Inconsistent units for yearly amount and supplier list",
        )

    def test_requires_issue_id_and_title(self):
        missing_id = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                }
            }
        )
        missing_title = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3980",
                }
            }
        )

        self.assertIsNone(missing_id)
        self.assertIsNone(missing_title)

    def test_ignores_update_payload_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["title"],
                "data": {
                    "identifier": "POI-3980",
                    "title": "Bug: Inconsistent units for yearly amount and supplier list",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
