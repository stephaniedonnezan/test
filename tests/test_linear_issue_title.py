import unittest

from automation.linear_issue_title import (
    RESEARCH_PREFIX,
    add_research_prefix,
    update_title_for_status_change,
    update_title_from_linear_event,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_adds_prefix_when_status_moves_to_research(self) -> None:
        title = "[5000] Fix Automate website on smaller screens"
        updated = update_title_for_status_change(title, "to research")
        self.assertEqual(updated, f"{RESEARCH_PREFIX}: {title}")

    def test_status_match_is_case_insensitive_and_trimmed(self) -> None:
        title = "Investigate API timeout"
        updated = update_title_for_status_change(title, "  To Research ")
        self.assertEqual(updated, f"{RESEARCH_PREFIX}: {title}")

    def test_prefix_is_not_duplicated(self) -> None:
        title = "Cursor researching: Investigate API timeout"
        updated = update_title_for_status_change(title, "to research")
        self.assertEqual(updated, title)

    def test_other_statuses_leave_title_unchanged(self) -> None:
        title = "Investigate API timeout"
        updated = update_title_for_status_change(title, "Canceled")
        self.assertEqual(updated, title)

    def test_can_update_directly_from_linear_event_payload(self) -> None:
        payload = {
            "triggerContext": {
                "title": "Investigate API timeout",
                "newStatus": "to research",
            }
        }
        self.assertEqual(
            update_title_from_linear_event(payload),
            "Cursor researching: Investigate API timeout",
        )


if __name__ == "__main__":
    unittest.main()
