import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4935",
                "title": "Issues indicator is mispositioned in container logic view",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4935",
                "title": "Cursor researching: Issues indicator is mispositioned in container logic view",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA UX/UI",
                "id": "POI-4935",
                "title": "Issues indicator is mispositioned in container logic view",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-1",
                "title": "Container logic issue",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Container logic issue",
            },
        )

    def test_accepts_status_field_fallback_for_direct_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to_research",
                "issueId": "POI-2",
                "title": "Needs research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "cursor researching: Already marked",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "Wrong trigger",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_prefixes_nested_linear_change_map(self):
        event = {
            "type": "Issue",
            "action": "update",
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Changed by map",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed by map",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "data": {
                "issue": {
                    "identifier": "POI-7",
                    "title": "Priority changed",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "No issue id",
            },
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-8",
            },
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
