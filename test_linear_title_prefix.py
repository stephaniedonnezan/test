import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4660",
                "title": "Site switch on the site name",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4660",
                "title": "Site switch on the site name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4660",
                "title": "Site switch on the site name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_researching_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4660",
                "title": "cursor researching: Site switch on the site name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4660",
                "title": "Site switch on the site name",
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4660")
        self.assertEqual(result["title"], "Cursor researching: Site switch on the site name")

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4660",
                    "title": "Site switch on the site name",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_requires_status_field_for_generic_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["assignee"],
            "data": {
                "issue": {
                    "identifier": "POI-4660",
                    "title": "Site switch on the site name",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_detects_status_change_from_changes_map(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "issue-id",
                "title": "Site switch on the site name",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Site switch on the site name",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4660 ",
                "title": "  Site switch on the site name  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_safely_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
