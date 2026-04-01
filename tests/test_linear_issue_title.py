import unittest

from linear_issue_title import (
    RESEARCHING_MARKER,
    updated_title_for_status_change,
    with_researching_prefix,
)


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Investigate endpoint retries"),
            f"{RESEARCHING_MARKER} - Investigate endpoint retries",
        )

    def test_keeps_existing_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Investigate endpoint retries"),
            "Cursor researching - Investigate endpoint retries",
        )

    def test_handles_blank_or_empty_bracket_title(self) -> None:
        self.assertEqual(with_researching_prefix("   "), RESEARCHING_MARKER)
        self.assertEqual(with_researching_prefix("[]"), RESEARCHING_MARKER)


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_updates_when_status_changes_to_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate endpoint retries",
            }
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Investigate endpoint retries",
        )

    def test_does_not_update_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "title": "Investigate endpoint retries",
            }
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_does_not_update_when_title_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Cursor researching: Investigate endpoint retries",
            }
        }
        self.assertIsNone(updated_title_for_status_change(payload))

    def test_accepts_root_payload_context(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }
        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Root payload title",
        )


if __name__ == "__main__":
    unittest.main()
