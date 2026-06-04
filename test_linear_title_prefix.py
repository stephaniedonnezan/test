import unittest

from linear_title_prefix import add_research_prefix
from linear_title_prefix import title_for_status_change
from linear_title_prefix import updated_title_from_payload


class AddResearchPrefixTests(unittest.TestCase):
    def test_prefixes_plain_title(self) -> None:
        self.assertEqual(
            add_research_prefix("Improve performance after the fix for POI-4469"),
            "Cursor researching: Improve performance after the fix for POI-4469",
        )

    def test_trims_plain_title(self) -> None:
        self.assertEqual(
            add_research_prefix("  Issue needing research  "),
            "Cursor researching: Issue needing research",
        )

    def test_empty_title_returns_prefix_only(self) -> None:
        self.assertEqual(add_research_prefix("  "), "Cursor researching")

    def test_does_not_duplicate_colon_prefix(self) -> None:
        self.assertEqual(
            add_research_prefix("Cursor researching: Existing title"),
            "Cursor researching: Existing title",
        )

    def test_does_not_duplicate_hyphen_prefix_case_insensitively(self) -> None:
        self.assertEqual(
            add_research_prefix("cursor researching - Existing title"),
            "cursor researching - Existing title",
        )


class TitleForStatusChangeTests(unittest.TestCase):
    def test_adds_prefix_for_to_research_status(self) -> None:
        self.assertEqual(
            title_for_status_change(
                "Improve performance after the fix for POI-4469",
                "to research",
            ),
            "Cursor researching: Improve performance after the fix for POI-4469",
        )

    def test_status_comparison_ignores_case_and_extra_whitespace(self) -> None:
        self.assertEqual(
            title_for_status_change("Issue title", "  To   Research "),
            "Cursor researching: Issue title",
        )

    def test_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            title_for_status_change("Issue title", "Done"),
            "Issue title",
        )


class UpdatedTitleFromPayloadTests(unittest.TestCase):
    def test_uses_cursor_automation_trigger_context(self) -> None:
        payload = {
            "automationId": "example",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Improve performance after the fix for POI-4469",
            },
        }

        self.assertEqual(
            updated_title_from_payload(payload),
            "Cursor researching: Improve performance after the fix for POI-4469",
        )

    def test_supports_raw_context_payload(self) -> None:
        self.assertEqual(
            updated_title_from_payload(
                {"newStatus": "to research", "title": "Issue title"}
            ),
            "Cursor researching: Issue title",
        )

    def test_returns_none_when_title_does_not_change(self) -> None:
        self.assertIsNone(
            updated_title_from_payload(
                {"triggerContext": {"newStatus": "Todo", "title": "Issue title"}}
            )
        )
        self.assertIsNone(
            updated_title_from_payload(
                {
                    "triggerContext": {
                        "newStatus": "to research",
                        "title": "Cursor researching: Issue title",
                    }
                }
            )
        )

    def test_returns_none_for_missing_or_invalid_fields(self) -> None:
        self.assertIsNone(updated_title_from_payload({"triggerContext": "bad"}))
        self.assertIsNone(updated_title_from_payload({"triggerContext": {}}))
        self.assertIsNone(
            updated_title_from_payload(
                {"triggerContext": {"newStatus": "to research", "title": None}}
            )
        )


if __name__ == "__main__":
    unittest.main()
