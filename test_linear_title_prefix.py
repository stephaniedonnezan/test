import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5039",
                "title": "Default emissions do not trickle down",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_accepts_automation_trigger_info_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5039",
                    "title": "Default emissions do not trickle down",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_normalizes_status_and_trigger_casing(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": " POI-5039 ",
            "title": " Default emissions do not trickle down ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5039",
            "title": "Default emissions do not trickle down",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5039",
            "title": "Default emissions do not trickle down",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5039",
            "title": "cursor researching: Default emissions do not trickle down",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5039",
                    "title": "Default emissions do not trickle down",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5039",
                    "title": "Default emissions do not trickle down",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "changes": {"state": {"old": "Backlog", "new": "To Research"}},
            "issueId": "POI-5039",
            "title": "Default emissions do not trickle down",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research"}

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
