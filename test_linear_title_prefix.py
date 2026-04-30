import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Allow UBA POS creation for methane",
            },
        )

    def test_supports_nested_linear_payload_shape(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Investigate certificate flow",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate certificate flow",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_fields(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "outer-id",
                "title": "Outer title",
                "data": {
                    "issue": {
                        "id": "inner-id",
                        "title": "Inner title",
                        "status": "Done",
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "outer-id",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "type": "status-changed",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-1",
            "title": "Normalize variants",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Normalize variants",
            },
        )

    def test_accepts_identifier_when_id_is_absent(self):
        event = {
            "trigger": "status changed",
            "status": "to research",
            "identifier": "POI-2",
            "title": "Use identifier",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Use identifier",
            },
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "  Trim this title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Trim this title",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching - Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "Wrong trigger",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-7",
            "title": "Wrong status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
