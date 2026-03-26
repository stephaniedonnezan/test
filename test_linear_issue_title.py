import copy
import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    apply_research_title_prefix,
    prefix_title,
    should_add_research_prefix,
)


class TestLinearIssueTitle(unittest.TestCase):
    def test_should_add_research_prefix_for_to_research_status(self) -> None:
        trigger_context = {"trigger": "status_changed", "newStatus": "to research"}
        self.assertTrue(should_add_research_prefix(trigger_context))

    def test_should_add_research_prefix_normalizes_status_variants(self) -> None:
        trigger_context = {"trigger": "status_changed", "newStatus": "To-Research"}
        self.assertTrue(should_add_research_prefix(trigger_context))

    def test_should_not_add_research_prefix_for_other_status_or_trigger(self) -> None:
        wrong_status = {"trigger": "status_changed", "newStatus": "In Progress"}
        wrong_trigger = {"trigger": "created", "newStatus": "to research"}
        self.assertFalse(should_add_research_prefix(wrong_status))
        self.assertFalse(should_add_research_prefix(wrong_trigger))

    def test_prefix_title_adds_prefix_once(self) -> None:
        original = "Deleting a counter reading"
        updated = prefix_title(original)
        self.assertEqual(updated, f"{RESEARCH_PREFIX}: {original}")
        self.assertEqual(prefix_title(updated), updated)

    def test_apply_research_title_prefix_updates_title_and_convenience_field(self) -> None:
        payload = {
            "automationId": "abc",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Deleting a counter reading",
            },
        }

        original_copy = copy.deepcopy(payload)
        updated = apply_research_title_prefix(payload)

        self.assertEqual(payload, original_copy)
        self.assertEqual(
            updated["triggerContext"]["title"],
            "Cursor researching: Deleting a counter reading",
        )
        self.assertEqual(
            updated["updatedTitle"],
            "Cursor researching: Deleting a counter reading",
        )

    def test_apply_research_title_prefix_noop_when_not_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "in progress",
                "title": "Deleting a counter reading",
            }
        }
        updated = apply_research_title_prefix(payload)
        self.assertEqual(updated, payload)


if __name__ == "__main__":
    unittest.main()
