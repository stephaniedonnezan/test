import unittest

from linear_issue_title import (
    RESEARCHING_MARKER,
    add_researching_prefix,
    normalize_status,
    should_prefix_researching,
    updated_title_from_payload,
)


class NormalizeStatusTests(unittest.TestCase):
    def test_normalize_status_handles_whitespace_and_case(self) -> None:
        self.assertEqual(normalize_status("  To   Research "), "to research")

    def test_normalize_status_non_string(self) -> None:
        self.assertEqual(normalize_status(None), "")


class ShouldPrefixResearchingTests(unittest.TestCase):
    def test_true_for_linear_issue_status_change_to_research(self) -> None:
        trigger_context = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
        }
        self.assertTrue(should_prefix_researching(trigger_context))

    def test_false_for_different_status(self) -> None:
        trigger_context = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "done",
        }
        self.assertFalse(should_prefix_researching(trigger_context))


class PrefixTitleTests(unittest.TestCase):
    def test_add_researching_prefix(self) -> None:
        self.assertEqual(
            add_researching_prefix("Dashboard: Selecting the current year breaks"),
            "Cursor researching: Dashboard: Selecting the current year breaks",
        )

    def test_does_not_duplicate_prefix(self) -> None:
        self.assertEqual(
            add_researching_prefix("Cursor researching: Existing title"),
            "Cursor researching: Existing title",
        )

    def test_empty_title_returns_marker(self) -> None:
        self.assertEqual(add_researching_prefix("   "), RESEARCHING_MARKER)


class PayloadTests(unittest.TestCase):
    def test_updated_title_from_nested_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Dashboard: Selecting the current year breaks",
            }
        }
        self.assertEqual(
            updated_title_from_payload(payload),
            "Cursor researching: Dashboard: Selecting the current year breaks",
        )

    def test_returns_none_when_no_update_needed(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "done",
                "title": "Dashboard: Selecting the current year breaks",
            }
        }
        self.assertIsNone(updated_title_from_payload(payload))


if __name__ == "__main__":
    unittest.main()
