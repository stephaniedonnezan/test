import unittest

from linear_issue_title import (
    CURSOR_RESEARCHING_PREFIX,
    build_title_update_from_event,
    update_title_for_status_change,
)


class UpdateTitleForStatusChangeTests(unittest.TestCase):
    def test_prefixes_title_when_status_is_to_research(self) -> None:
        self.assertEqual(
            update_title_for_status_change(
                title="Investigate mass balance transport emissions",
                new_status="to research",
            ),
            f"{CURSOR_RESEARCHING_PREFIX}: Investigate mass balance transport emissions",
        )

    def test_does_not_prefix_title_for_other_statuses(self) -> None:
        self.assertEqual(
            update_title_for_status_change(
                title="Investigate mass balance transport emissions",
                new_status="Canceled",
            ),
            "Investigate mass balance transport emissions",
        )

    def test_does_not_duplicate_prefix(self) -> None:
        original = f"{CURSOR_RESEARCHING_PREFIX}: Existing issue title"
        self.assertEqual(
            update_title_for_status_change(
                title=original,
                new_status="to research",
            ),
            original,
        )

    def test_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            update_title_for_status_change(
                title="Normalize status label handling",
                new_status="  To Research ",
            ),
            f"{CURSOR_RESEARCHING_PREFIX}: Normalize status label handling",
        )


class BuildTitleUpdateFromEventTests(unittest.TestCase):
    def test_returns_should_update_true_when_title_changes(self) -> None:
        payload = build_title_update_from_event(
            {
                "triggerContext": {
                    "newStatus": "to research",
                    "title": "Sample issue",
                }
            }
        )
        self.assertEqual(
            payload,
            {
                "should_update": True,
                "title": f"{CURSOR_RESEARCHING_PREFIX}: Sample issue",
            },
        )

    def test_returns_should_update_false_when_title_unchanged(self) -> None:
        payload = build_title_update_from_event(
            {
                "triggerContext": {
                    "newStatus": "In Progress",
                    "title": "Sample issue",
                }
            }
        )
        self.assertEqual(
            payload,
            {
                "should_update": False,
                "title": "Sample issue",
            },
        )

    def test_supports_flat_event_payload(self) -> None:
        payload = build_title_update_from_event(
            {
                "newStatus": "to research",
                "title": "Flat payload issue",
            }
        )
        self.assertEqual(payload["should_update"], True)
        self.assertEqual(
            payload["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Flat payload issue",
        )


if __name__ == "__main__":
    unittest.main()
