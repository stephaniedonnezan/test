import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    apply_title_rule,
    maybe_update_issue_title,
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

    def test_should_prefix_with_case_and_spacing_variations(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "  To   Research  ",
            }
        }

        self.assertTrue(should_prefix_title(event))

    def test_should_not_prefix_for_other_status(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
            }
        }

        self.assertFalse(should_prefix_title(event))

    def test_should_not_prefix_for_other_trigger(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
            }
        }

        self.assertFalse(should_prefix_title(event))

    def test_apply_title_rule_prefixes_nested_payload_title(self) -> None:
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
        self.assertEqual(event["triggerContext"]["title"], "Deleting a counter reading")

    def test_apply_title_rule_prefixes_root_payload_title(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }

        updated = apply_title_rule(event)

        self.assertEqual(updated["title"], f"{RESEARCH_PREFIX} Root payload title")

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

    def test_with_research_prefix_handles_empty_title(self) -> None:
        self.assertEqual(with_research_prefix("   "), RESEARCH_PREFIX)

    def test_maybe_update_issue_title_returns_title_or_none(self) -> None:
        matching_event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate endpoint retries",
            }
        }
        skipped_event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "title": "Investigate endpoint retries",
            }
        }

        self.assertEqual(
            maybe_update_issue_title(matching_event),
            f"{RESEARCH_PREFIX} Investigate endpoint retries",
        )
        self.assertIsNone(maybe_update_issue_title(skipped_event))


if __name__ == "__main__":
    unittest.main()
