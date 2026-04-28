import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4548",
                "title": "Company Insights Dashboard not working",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Company Insights Dashboard not working",
            },
        )

    def test_accepts_flat_payload(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4548",
            "title": "Container sites dashboard issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Container sites dashboard issue",
            },
        )

    def test_uses_status_when_new_status_is_absent(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4548",
                "title": "Research this issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_accepts_issue_id_field(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": "POI-4548",
                "title": "Research this issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_matches_status_and_trigger_case_insensitively(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "STATUS CHANGED",
                "newStatus": "to_research",
                "id": "POI-4548",
                "title": "Normalize fields",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Normalize fields",
            },
        )

    def test_does_not_update_non_status_change_events(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "created",
                "newStatus": "To Research",
                "id": "POI-4548",
                "title": "New issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4548",
                "title": "Started issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4548",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4548",
                "title": "  Needs research  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4548",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_requires_issue_id_and_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Missing id",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4548",
                    }
                }
            )
        )

    def test_ignores_non_mapping_events(self) -> None:
        self.assertIsNone(build_issue_title_update(None))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
