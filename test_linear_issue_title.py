import unittest

from linear_issue_title import add_research_prefix_on_status_change


class TestAddResearchPrefixOnStatusChange(unittest.TestCase):
    def test_adds_prefix_when_status_is_to_research(self) -> None:
        payload = {"newStatus": "to research", "title": "Ensure we can re-open a delivery"}

        updated = add_research_prefix_on_status_change(payload)

        self.assertEqual(
            updated["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )
        self.assertEqual(payload["title"], "Ensure we can re-open a delivery")

    def test_does_not_duplicate_existing_prefix(self) -> None:
        payload = {"newStatus": "to research", "title": "Cursor researching: Existing title"}

        updated = add_research_prefix_on_status_change(payload)

        self.assertEqual(updated["title"], "Cursor researching: Existing title")

    def test_does_not_change_other_status(self) -> None:
        payload = {"newStatus": "In Review", "title": "Ensure we can re-open a delivery"}

        updated = add_research_prefix_on_status_change(payload)

        self.assertEqual(updated["title"], "Ensure we can re-open a delivery")


if __name__ == "__main__":
    unittest.main()
