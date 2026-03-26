import unittest

from linear_title_updater import (
    RESEARCH_PREFIX,
    add_research_prefix,
    compute_title_from_trigger,
    should_add_research_prefix,
)


class TestLinearTitleUpdater(unittest.TestCase):
    def test_should_add_research_prefix_matches_to_research(self) -> None:
        self.assertTrue(should_add_research_prefix("To Research"))
        self.assertTrue(should_add_research_prefix("to research"))
        self.assertTrue(should_add_research_prefix("  TO RESEARCH "))
        self.assertFalse(should_add_research_prefix("In Progress"))

    def test_add_research_prefix_adds_when_missing(self) -> None:
        title = "Replace 'Last 12 months' with 'year to date' in UI"
        updated = add_research_prefix(title)
        self.assertEqual(updated, f"{RESEARCH_PREFIX}: {title}")

    def test_add_research_prefix_is_idempotent(self) -> None:
        title = "Cursor researching: Existing title"
        self.assertEqual(add_research_prefix(title), title)
        bracketed = "[Cursor researching] Existing title"
        self.assertEqual(add_research_prefix(bracketed), bracketed)

    def test_compute_title_from_trigger_adds_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "To Research",
                "title": "Replace 'Last 12 months' with 'year to date' in UI",
            }
        }
        title, changed = compute_title_from_trigger(payload)
        self.assertTrue(changed)
        self.assertEqual(
            title,
            "Cursor researching: Replace 'Last 12 months' with 'year to date' in UI",
        )

    def test_compute_title_from_trigger_no_change_when_other_status(self) -> None:
        payload = {
            "triggerContext": {"newStatus": "Done", "title": "My issue title"},
        }
        title, changed = compute_title_from_trigger(payload)
        self.assertFalse(changed)
        self.assertEqual(title, "My issue title")


if __name__ == "__main__":
    unittest.main()
