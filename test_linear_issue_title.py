import unittest

from linear_issue_title import (
    RESEARCHING_PREFIX,
    updated_title_for_status_change,
    with_researching_prefix,
)


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Edit a qualified input shouldn't prompt user to select contract"),
            f"{RESEARCHING_PREFIX} - Edit a qualified input shouldn't prompt user to select contract",
        )

    def test_keeps_existing_prefix_with_dash(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Existing title"),
            "Cursor researching - Existing title",
        )

    def test_keeps_existing_prefix_with_colon(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching: Existing title"),
            "Cursor researching: Existing title",
        )

    def test_handles_blank_title(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCHING_PREFIX)


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_on_to_research(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Edit a qualified input shouldn't prompt user to select contract",
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Edit a qualified input shouldn't prompt user to select contract",
        )

    def test_updates_with_nested_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Edit a qualified input shouldn't prompt user to select contract",
            }
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Edit a qualified input shouldn't prompt user to select contract",
        )

    def test_ignores_other_statuses(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "title": "Some issue",
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_other_triggers(self) -> None:
        payload = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "title": "Some issue",
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_returns_none_when_already_prefixed(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Cursor researching - Existing title",
        }
        self.assertIsNone(updated_title_for_status_change(payload))


if __name__ == "__main__":
    unittest.main()
