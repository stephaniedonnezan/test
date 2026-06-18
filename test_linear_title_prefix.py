import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_payload(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2664",
            "title": "Onboarding flow bug",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Onboarding flow bug",
            },
        )

    def test_prefixes_automation_trigger_context_payload(self) -> None:
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2664",
                "title": "Unhandled rejection",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Unhandled rejection",
            },
        )

    def test_prefixes_nested_trigger_context_issue_payload(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "data": {
                    "issue": {
                        "id": "issue-id",
                        "title": "Nested issue title",
                    },
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_prefixes_linear_update_payload_with_state_name(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-2664",
                    "title": "Linear webhook title",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Linear webhook title",
            },
        )

    def test_outer_fields_override_nested_issue_fields(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "outer-id",
                "title": "Outer title",
                "data": {
                    "issue": {
                        "id": "nested-id",
                        "title": "Nested title",
                        "state": {"name": "Backlog"},
                    },
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "outer-id",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_skips_non_status_change_trigger(self) -> None:
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-2664",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_research_status(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "Triage",
            "id": "POI-2664",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_title_case_insensitively(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2664",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_blank_title(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2664",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
