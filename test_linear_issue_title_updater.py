import unittest

from linear_issue_title_updater import (
    RESEARCH_PREFIX,
    TO_RESEARCH_STATUS,
    ensure_prefix,
    update_issue_title_on_status_change,
    updated_title_for_status_change,
    with_researching_prefix,
)


class PrefixHelpersTests(unittest.TestCase):
    def test_with_researching_prefix_adds_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Indicative view on GHG emissions"),
            f"{RESEARCH_PREFIX} - Indicative view on GHG emissions",
        )

    def test_with_researching_prefix_avoids_duplicate(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching: Indicative view on GHG emissions"),
            "Cursor researching: Indicative view on GHG emissions",
        )

    def test_with_researching_prefix_handles_blank_title(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCH_PREFIX)

    def test_ensure_prefix_compatibility_wrapper(self) -> None:
        self.assertEqual(
            ensure_prefix("Issue title"),
            f"{RESEARCH_PREFIX} - Issue title",
        )


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_on_to_research_status(self) -> None:
        payload = {
            "newStatus": TO_RESEARCH_STATUS,
            "title": "Indicative view on GHG emissions",
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Indicative view on GHG emissions",
        )

    def test_ignores_non_matching_status(self) -> None:
        payload = {
            "newStatus": "In Progress",
            "title": "Indicative view on GHG emissions",
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_ignores_when_title_already_prefixed(self) -> None:
        payload = {
            "newStatus": "To Research",
            "title": "Cursor researching - Indicative view on GHG emissions",
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_accepts_payload_with_nested_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "  To   Research  ",
                "title": "Indicative view on GHG emissions",
            }
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Indicative view on GHG emissions",
        )

    def test_requires_status_changed_trigger_when_trigger_present(self) -> None:
        payload = {
            "trigger": "comment_created",
            "newStatus": TO_RESEARCH_STATUS,
            "title": "Indicative view on GHG emissions",
        }
        self.assertIsNone(updated_title_for_status_change(payload))


class UpdateIssueTitleOnStatusChangeTests(unittest.TestCase):
    def test_returns_title_update_when_status_moves_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Indicative view on GHG emissions",
                "id": "POI-3804",
            }
        }
        self.assertEqual(
            update_issue_title_on_status_change(payload),
            {
                "issueId": "POI-3804",
                "oldTitle": "Indicative view on GHG emissions",
                "newTitle": "Cursor researching - Indicative view on GHG emissions",
            },
        )

    def test_returns_none_without_issue_id(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Indicative view on GHG emissions",
            }
        }
        self.assertIsNone(update_issue_title_on_status_change(payload))

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "Indicative view on GHG emissions",
                "id": "POI-3804",
            }
        }
        self.assertIsNone(update_issue_title_on_status_change(payload))


if __name__ == "__main__":
    unittest.main()
