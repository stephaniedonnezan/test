import unittest

from linear_title_update import (
    RESEARCH_PREFIX,
    add_research_prefix,
    should_mark_researching,
    updated_issue_title,
)


class LinearTitleUpdateTests(unittest.TestCase):
    def test_should_mark_researching_on_matching_status_event(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            }
        }
        self.assertTrue(should_mark_researching(payload))

    def test_should_not_mark_researching_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "in review",
            }
        }
        self.assertFalse(should_mark_researching(payload))

    def test_add_research_prefix_once(self) -> None:
        original = "Company Insights Concept (Dashboard)"
        updated = add_research_prefix(original)
        self.assertEqual(
            updated, f"{RESEARCH_PREFIX} - Company Insights Concept (Dashboard)"
        )

        updated_again = add_research_prefix(updated)
        self.assertEqual(updated_again, updated)

    def test_updated_issue_title_returns_none_when_not_applicable(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "in review",
                "title": "Some title",
            }
        }
        self.assertIsNone(updated_issue_title(payload))

    def test_updated_issue_title_returns_prefixed_title(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Some title",
            }
        }
        self.assertEqual(updated_issue_title(payload), f"{RESEARCH_PREFIX} - Some title")


if __name__ == "__main__":
    unittest.main()
