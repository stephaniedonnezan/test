import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_nested_to_research_event(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4578",
                "title": "[Container Logic] Ability to Add input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4578",
                "title": "Cursor researching: [Container Logic] Ability to Add input",
            },
        )

    def test_builds_title_update_for_flat_payload(self) -> None:
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "issueId": "POI-1",
            "title": "Investigate behavior",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate behavior",
            },
        )

    def test_supports_nested_issue_fields(self) -> None:
        event = {
            "trigger": "status_changed",
            "newState": {"name": "to-research"},
            "issue": {
                "id": "POI-2",
                "title": "Check Linear state payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check Linear state payload",
            },
        )

    def test_ignores_non_status_change_events(self) -> None:
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicating_existing_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_titles(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payload_without_issue_id(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self) -> None:
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
