import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    apply_title_rule,
    should_prefix_title,
    with_research_prefix,
)


class LinearIssueTitleRuleTests(unittest.TestCase):
    def test_should_prefix_when_status_changed_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            }
        }
        self.assertTrue(should_prefix_title(event))

    def test_should_not_prefix_for_other_status(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "in review",
            }
        }
        self.assertFalse(should_prefix_title(event))

    def test_apply_title_rule_prefixes_title(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Deleting a counter reading",
            }
        }
        updated = apply_title_rule(event)
        self.assertEqual(
            updated["triggerContext"]["title"],
            f"{RESEARCH_PREFIX} Deleting a counter reading",
        )

    def test_apply_title_rule_avoids_double_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": f"{RESEARCH_PREFIX} Deleting a counter reading",
            }
        }
        updated = apply_title_rule(event)
        self.assertEqual(
            updated["triggerContext"]["title"],
            f"{RESEARCH_PREFIX} Deleting a counter reading",
        )

    def test_with_research_prefix_strips_whitespace(self) -> None:
        self.assertEqual(
            with_research_prefix("  Deleting a counter reading  "),
            f"{RESEARCH_PREFIX} Deleting a counter reading",
        )


if __name__ == "__main__":
    unittest.main()
