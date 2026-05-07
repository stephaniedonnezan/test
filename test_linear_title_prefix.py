import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4645",
                "title": "Logger.errorWithTags",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4645",
                "title": "Cursor researching: Logger.errorWithTags",
            },
        )

    def test_accepts_case_and_separator_variants(self) -> None:
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-1",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_accepts_nested_linear_issue_payload(self) -> None:
        event = {
            "action": "status changed",
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_ignores_non_status_change_triggers(self) -> None:
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4",
            "title": "Wrong status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self) -> None:
        missing_id = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing ID",
        }
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_safely_ignores_non_mapping_payloads(self) -> None:
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
