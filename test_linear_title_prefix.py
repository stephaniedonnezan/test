import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4484",
                "title": "Rework Container Closing Tab Flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4484",
                "title": "Cursor researching: Rework Container Closing Tab Flow",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-1",
            "title": "Investigate edge case",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate edge case",
            },
        )

    def test_accepts_snake_case_new_status_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to_research",
            "issue_id": "POI-2",
            "title": "Audit workflow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Audit workflow",
            },
        )

    def test_accepts_camel_case_trigger_and_hyphenated_status(self):
        event = {
            "action": "statusChanged",
            "status": "to-research",
            "issueId": "POI-3",
            "title": "Map webhook payloads",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Map webhook payloads",
            },
        )

    def test_uses_state_name_status_fallback(self):
        event = {
            "type": "statusChanged",
            "state": {"name": "To Research"},
            "identifier": "POI-4",
            "title": "Clarify status source",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Clarify status source",
            },
        )

    def test_reads_nested_linear_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-5",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_reads_top_level_issue_payload(self):
        event = {
            "webhookType": "status_changed",
            "issue": {
                "id": "POI-6",
                "title": "Top-level issue payload",
            },
            "status": "to research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Top-level issue payload",
            },
        )

    def test_does_not_prefix_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-7",
            "title": "Ready for QA",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_prefix_for_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "Comment notification",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "Cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "cursor researching: Existing lowercase prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "  POI-11  ",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-11",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_returns_none_for_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-12",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_event(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
