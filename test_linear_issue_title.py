import unittest

from linear_issue_title import (
    add_research_prefix,
    should_mark_as_research,
    update_issue_title_for_status_change,
)


class TestLinearIssueTitle(unittest.TestCase):
    def test_should_mark_as_research_accepts_casing_and_separators(self) -> None:
        self.assertTrue(should_mark_as_research("to research"))
        self.assertTrue(should_mark_as_research("To_Research"))
        self.assertTrue(should_mark_as_research("to-research"))
        self.assertFalse(should_mark_as_research("canceled"))

    def test_add_research_prefix_adds_once(self) -> None:
        title = "UX/UI design"
        updated = add_research_prefix(title)
        self.assertEqual(updated, "Cursor researching: UX/UI design")
        self.assertEqual(add_research_prefix(updated), updated)

    def test_update_title_when_status_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "title": "UX/UI design",
                "newStatus": "to research",
            }
        }
        changed, new_title = update_issue_title_for_status_change(payload)
        self.assertTrue(changed)
        self.assertEqual(new_title, "Cursor researching: UX/UI design")
        self.assertEqual(
            payload["triggerContext"]["title"], "Cursor researching: UX/UI design"
        )

    def test_no_update_for_other_status(self) -> None:
        payload = {"triggerContext": {"title": "UX/UI design", "newStatus": "canceled"}}
        changed, new_title = update_issue_title_for_status_change(payload)
        self.assertFalse(changed)
        self.assertEqual(new_title, "UX/UI design")
        self.assertEqual(payload["triggerContext"]["title"], "UX/UI design")


if __name__ == "__main__":
    unittest.main()
