import unittest

from linear_issue_title import (
    RESEARCHING_PREFIX,
    updated_title_for_status_change,
    with_researching_prefix,
)


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Add column labels"),
            f"{RESEARCHING_PREFIX} - Add column labels",
        )

    def test_keeps_existing_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Add column labels"),
            "Cursor researching - Add column labels",
        )

    def test_handles_blank_title(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCHING_PREFIX)


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_on_to_research_status(self) -> None:
        payload = {
            "newStatus": "to research",
            "title": "Add column labels to the Mass Balance canvas",
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Add column labels to the Mass Balance canvas",
        )

    def test_ignores_non_matching_status(self) -> None:
        payload = {
            "newStatus": "In Progress",
            "title": "Add column labels to the Mass Balance canvas",
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_when_title_already_prefixed(self) -> None:
        payload = {
            "newStatus": "To Research",
            "title": "Cursor researching: Add column labels to the Mass Balance canvas",
        }
        self.assertIsNone(updated_title_for_status_change(payload))


if __name__ == "__main__":
    unittest.main()
