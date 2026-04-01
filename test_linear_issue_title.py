import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    add_research_prefix,
    updated_title_from_payload,
    updated_title_from_status_change,
)


class TestLinearIssueTitle(unittest.TestCase):
    def test_add_prefix_when_status_is_to_research(self) -> None:
        title = "Buttons bar disappearing sometimes from the mass balance"
        result = updated_title_from_status_change(title, "to research")
        self.assertEqual(f"{RESEARCH_PREFIX} {title}", result)

    def test_add_prefix_when_status_uses_different_separators(self) -> None:
        title = "Some issue"
        self.assertEqual(
            f"{RESEARCH_PREFIX} {title}",
            updated_title_from_status_change(title, "to_research"),
        )
        self.assertEqual(
            f"{RESEARCH_PREFIX} {title}",
            updated_title_from_status_change(title, "to-research"),
        )

    def test_does_not_duplicate_prefix(self) -> None:
        title = f"{RESEARCH_PREFIX} Already prefixed"
        self.assertEqual(title, add_research_prefix(title))
        self.assertEqual(title, updated_title_from_status_change(title, "to research"))

    def test_other_statuses_keep_title_unchanged(self) -> None:
        title = "Original title"
        self.assertEqual(title, updated_title_from_status_change(title, "Done"))
        self.assertEqual(title, updated_title_from_status_change(title, "In progress"))
        self.assertEqual(title, updated_title_from_status_change(title, None))

    def test_payload_shape_from_cursor_automation(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "Buttons bar disappearing sometimes from the mass balance",
            }
        }
        self.assertEqual(
            "Cursor researching Buttons bar disappearing sometimes from the mass balance",
            updated_title_from_payload(payload),
        )


if __name__ == "__main__":
    unittest.main()
